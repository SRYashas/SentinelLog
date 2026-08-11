/**
 * SentinelLog — Collector Service (Main Entry Point)
 * =====================================================
 * Orchestrates the full event collection pipeline:
 *
 *   1. Connect to MongoDB
 *   2. Load last-polled timestamps from State collection (gap resilience)
 *   3. Start polling loop (every 5 seconds):
 *      a. Read events from Sysmon + PowerShell event logs
 *      b. Deduplicate against already-stored events (by eventRecordId)
 *      c. Run origin resolver on process_create events
 *      d. Run rules engine on all events
 *      e. Batch insert enriched events into MongoDB
 *      f. Update last-polled timestamps
 *   4. Handle graceful shutdown (SIGINT/SIGTERM)
 *
 * Run directly:  node index.js
 * As a service:  node install-service.js (then manage via services.msc)
 */

const { connectDB, Event, getLastTimestamp, setLastTimestamp } = require('./db');
const { readSysmonEvents, readPowerShellEvents } = require('./eventLogReader');
const { resolveOrigin, forceRefreshCache } = require('./originResolver');
const { evaluateFullRisk } = require('./rules');

// ── Configuration ──────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 5000; // 5 seconds between polls
const STATE_KEY_SYSMON = 'lastTimestamp_sysmon';
const STATE_KEY_POWERSHELL = 'lastTimestamp_powershell';

// ── Polling Loop ───────────────────────────────────────────────────────────

let isRunning = true;
let pollTimer = null;

/**
 * Single poll cycle: read events, enrich, store.
 */
async function pollCycle() {
  if (!isRunning) return;

  try {
    // ── Step 1: Read last-polled timestamps ────────────────────────────
    const lastSysmon = await getLastTimestamp(STATE_KEY_SYSMON);
    const lastPS = await getLastTimestamp(STATE_KEY_POWERSHELL);

    // ── Step 2: Read new events from both channels ────────────────────
    const [sysmonResult, psResult] = await Promise.all([
      readSysmonEvents(lastSysmon),
      readPowerShellEvents(lastPS)
    ]);

    const allEvents = [...sysmonResult.events, ...psResult.events];

    if (allEvents.length === 0) {
      return; // Nothing new, skip
    }

    console.log(`[Collector] Found ${sysmonResult.events.length} Sysmon + ${psResult.events.length} PowerShell events`);

    // ── Step 3: Deduplicate ───────────────────────────────────────────
    // Check which eventRecordIds are already in the database
    const recordIds = allEvents
      .map(e => e.eventRecordId)
      .filter(id => id && id.length > 0);

    let existingIds = new Set();
    if (recordIds.length > 0) {
      const existing = await Event.find(
        { eventRecordId: { $in: recordIds } },
        { eventRecordId: 1 }
      ).lean();
      existingIds = new Set(existing.map(e => e.eventRecordId));
    }

    const newEvents = allEvents.filter(e =>
      !e.eventRecordId || !existingIds.has(e.eventRecordId)
    );

    if (newEvents.length === 0) {
      // Update timestamps even if all were duplicates
      if (sysmonResult.latestTimestamp) {
        await setLastTimestamp(STATE_KEY_SYSMON, sysmonResult.latestTimestamp);
      }
      if (psResult.latestTimestamp) {
        await setLastTimestamp(STATE_KEY_POWERSHELL, psResult.latestTimestamp);
      }
      return;
    }

    // ── Step 4: Enrich — Origin Resolution + Risk Evaluation ──────────
    const enrichedEvents = [];
    for (const event of newEvents) {
      // Origin resolution (only meaningful for process_create events)
      if (event.eventType === 'process_create') {
        event.origin = await resolveOrigin(event);
      } else {
        // Script block and module log events don't have process origin context
        event.origin = {
          resolved: true,
          source: 'user_interactive',
          detail: 'PowerShell logging event'
        };
      }

      // Risk evaluation (runs against all event types)
      const risk = evaluateFullRisk(event);
      event.riskLevel = risk.riskLevel;
      event.riskReasons = risk.riskReasons;

      enrichedEvents.push(event);
    }

    // ── Step 5: Batch insert into MongoDB ─────────────────────────────
    try {
      await Event.insertMany(enrichedEvents, { ordered: false });
      console.log(`[Collector] Stored ${enrichedEvents.length} new events`);
    } catch (err) {
      // insertMany with ordered:false continues past duplicates
      if (err.code === 11000) {
        console.log(`[Collector] Some duplicate events skipped`);
      } else {
        console.error('[Collector] Insert error:', err.message);
      }
    }

    // ── Step 6: Update last-polled timestamps ─────────────────────────
    if (sysmonResult.latestTimestamp) {
      await setLastTimestamp(STATE_KEY_SYSMON, sysmonResult.latestTimestamp);
    }
    if (psResult.latestTimestamp) {
      await setLastTimestamp(STATE_KEY_POWERSHELL, psResult.latestTimestamp);
    }

    // Log high-risk events to console for immediate visibility
    const highRisk = enrichedEvents.filter(e => e.riskLevel === 'high');
    if (highRisk.length > 0) {
      console.log(`[Collector] ⚠ ${highRisk.length} HIGH-RISK events detected:`);
      for (const e of highRisk) {
        console.log(`  → ${e.processName}: ${e.commandLine.substring(0, 120)}`);
        console.log(`    Reasons: ${e.riskReasons.join(', ')}`);
      }
    }

  } catch (err) {
    console.error('[Collector] Poll cycle error:', err.message);
  }
}

// ── Main Entry Point ───────────────────────────────────────────────────────

async function main() {
  console.log('+--------------------------------------------+');
  console.log('|  SentinelLog Collector Service             |');
  console.log('|  Offline Windows Process & Console Monitor |');
  console.log('+--------------------------------------------+');
  console.log('');

  // Connect to MongoDB
  await connectDB();

  // Pre-populate the origin resolver cache
  console.log('[Collector] Initializing origin resolver...');
  await forceRefreshCache();

  // Check for last-polled timestamps (gap resilience)
  const lastSysmon = await getLastTimestamp(STATE_KEY_SYSMON);
  const lastPS = await getLastTimestamp(STATE_KEY_POWERSHELL);
  if (lastSysmon) {
    console.log(`[Collector] Resuming Sysmon from: ${lastSysmon}`);
  } else {
    console.log('[Collector] First run — will capture all available Sysmon events');
  }
  if (lastPS) {
    console.log(`[Collector] Resuming PowerShell from: ${lastPS}`);
  } else {
    console.log('[Collector] First run — will capture all available PowerShell events');
  }

  console.log(`[Collector] Starting poll loop (interval: ${POLL_INTERVAL_MS / 1000}s)`);
  console.log('');

  // Initial poll immediately
  await pollCycle();

  // Start recurring poll
  pollTimer = setInterval(async () => {
    await pollCycle();
  }, POLL_INTERVAL_MS);
}

// ── Graceful Shutdown ──────────────────────────────────────────────────────

function shutdown(signal) {
  console.log(`\n[Collector] Received ${signal}, shutting down gracefully...`);
  isRunning = false;

  if (pollTimer) {
    clearInterval(pollTimer);
  }

  // Give in-flight operations a moment to complete
  setTimeout(() => {
    console.log('[Collector] Shutdown complete.');
    process.exit(0);
  }, 2000);
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

// Windows-specific: handle Ctrl+C on Windows
if (process.platform === 'win32') {
  const readline = require('readline');
  const rl = readline.createInterface({ input: process.stdin });
  rl.on('SIGINT', () => shutdown('SIGINT'));
}

// Start the collector
main().catch(err => {
  console.error('[Collector] Fatal error:', err);
  process.exit(1);
});
