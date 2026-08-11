/**
 * SentinelLog — Event Log Reader
 * ================================
 * Polls Windows Event Log channels via `wevtutil` and parses XML output.
 *
 * Monitored channels:
 *   1. Microsoft-Windows-Sysmon/Operational → Event ID 1 (ProcessCreate)
 *   2. Microsoft-Windows-PowerShell/Operational → Event ID 4104 (ScriptBlock), 4103 (ModuleLog)
 *
 * Uses XPath time-range filters with the last-polled timestamp from the State
 * collection for gap resilience — if the collector restarts, it picks up from
 * where it left off instead of losing events.
 *
 * XML is parsed via xml2js with namespace stripping for clean field access.
 */

const { execFile } = require('child_process');
const xml2js = require('xml2js');
const path = require('path');

// ── XML Parser Setup ───────────────────────────────────────────────────────

const xmlParser = new xml2js.Parser({
  explicitArray: false,
  tagNameProcessors: [xml2js.processors.stripPrefix],
  attrNameProcessors: [xml2js.processors.stripPrefix]
});

/**
 * Parse an XML string into a JS object.
 */
function parseXML(xmlString) {
  return new Promise((resolve, reject) => {
    xmlParser.parseString(xmlString, (err, result) => {
      if (err) reject(err);
      else resolve(result);
    });
  });
}

// ── wevtutil Query Builder ─────────────────────────────────────────────────

/**
 * Build an XPath query for wevtutil that filters by Event ID and optionally
 * by a time range (events after a given timestamp).
 *
 * @param {number[]} eventIds - Array of Event IDs to filter for
 * @param {string|null} sinceTimestamp - ISO 8601 timestamp for time filtering, or null for all events
 * @returns {string} XPath query string
 */
function buildXPathQuery(eventIds, sinceTimestamp) {
  // Build the EventID filter: (EventID=1) or (EventID=1 or EventID=4104)
  const idFilter = eventIds.length === 1
    ? `EventID=${eventIds[0]}`
    : eventIds.map(id => `EventID=${id}`).join(' or ');

  if (sinceTimestamp) {
    // Convert ISO timestamp to the SystemTime format wevtutil expects
    // wevtutil uses: TimeCreated[@SystemTime>='2024-01-01T00:00:00.000Z']
    return `*[System[(${idFilter}) and TimeCreated[@SystemTime>='${sinceTimestamp}']]]`;
  }

  return `*[System[${idFilter}]]`;
}

/**
 * Execute wevtutil to query events from a specific channel.
 *
 * @param {string} channel - Event log channel name
 * @param {string} query - XPath query
 * @param {number} maxEvents - Maximum events to retrieve per poll (prevents overwhelming)
 * @returns {Promise<string>} Raw XML output
 */
function queryEventLog(channel, query, maxEvents = 500) {
  return new Promise((resolve, reject) => {
    const args = [
      'qe',
      channel,
      `/q:${query}`,
      '/f:xml',
      '/rd:false',  // Read oldest first (chronological order)
      `/c:${maxEvents}`
    ];

    execFile('wevtutil', args, { maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        // Exit code 15007 = "The specified query is invalid" (often means no events match)
        // Exit code 1 with empty stderr often means no events found
        if (stderr && stderr.includes('No events')) {
          resolve('');
          return;
        }
        // If the channel doesn't exist yet (Sysmon not installed), don't crash
        if (stderr && (stderr.includes('not found') || stderr.includes('The specified channel'))) {
          console.warn(`[EventLogReader] Channel not found: ${channel}. Is Sysmon installed?`);
          resolve('');
          return;
        }
        // Some wevtutil errors return exit code 1 but still have valid output
        if (stdout && stdout.trim().length > 0) {
          resolve(stdout);
          return;
        }
        reject(new Error(`wevtutil error for ${channel}: ${stderr || error.message}`));
        return;
      }
      resolve(stdout || '');
    });
  });
}

// ── Event Normalizer ───────────────────────────────────────────────────────

/**
 * Extract a named Data element from Sysmon EventData.
 * Sysmon events store fields as <Data Name="FieldName">Value</Data>
 */
function getEventDataField(dataArray, fieldName) {
  if (!dataArray) return '';
  // dataArray can be a single object or an array
  const items = Array.isArray(dataArray) ? dataArray : [dataArray];
  const field = items.find(d => d && d.$ && d.$.Name === fieldName);
  if (!field) return '';
  // The value can be the text content (string) or nested
  return typeof field === 'string' ? field : (field._ || field.toString() || '');
}

/**
 * Extract the process name from a full image path.
 * e.g., "C:\Windows\System32\cmd.exe" → "cmd.exe"
 */
function extractProcessName(imagePath) {
  if (!imagePath) return '';
  return path.basename(imagePath).toLowerCase();
}

/**
 * Normalize a Sysmon Event ID 1 (ProcessCreate) into our schema format.
 */
function normalizeSysmonEvent(parsed) {
  try {
    const system = parsed.Event.System;
    const eventData = parsed.Event.EventData;
    const data = eventData ? eventData.Data : [];

    const image = getEventDataField(data, 'Image');
    const parentImage = getEventDataField(data, 'ParentImage');

    return {
      timestamp: new Date(getEventDataField(data, 'UtcTime') || system.TimeCreated.$.SystemTime),
      eventType: 'process_create',
      processName: extractProcessName(image),
      commandLine: getEventDataField(data, 'CommandLine'),
      pid: parseInt(getEventDataField(data, 'ProcessId'), 10) || 0,
      parentProcessName: extractProcessName(parentImage),
      parentCommandLine: getEventDataField(data, 'ParentCommandLine'),
      parentPid: parseInt(getEventDataField(data, 'ParentProcessId'), 10) || 0,
      user: getEventDataField(data, 'User'),
      hash: {
        sha256: extractHash(getEventDataField(data, 'Hashes'), 'SHA256')
      },
      scriptBlockText: '',
      eventRecordId: system.EventRecordID || ''
    };
  } catch (err) {
    console.error('[EventLogReader] Failed to normalize Sysmon event:', err.message);
    return null;
  }
}

/**
 * Extract a specific hash type from the Sysmon Hashes field.
 * Format: "SHA256=ABC123,MD5=DEF456"
 */
function extractHash(hashString, algorithm) {
  if (!hashString) return '';
  const prefix = `${algorithm}=`;
  const parts = hashString.split(',');
  const match = parts.find(p => p.trim().startsWith(prefix));
  return match ? match.trim().substring(prefix.length) : '';
}

/**
 * Normalize a PowerShell Event ID 4104 (Script Block Logging) event.
 */
function normalizePSScriptBlock(parsed) {
  try {
    const system = parsed.Event.System;
    const eventData = parsed.Event.EventData;
    const data = eventData ? eventData.Data : [];

    // Script Block events store the script text in the "ScriptBlockText" field
    const scriptText = getEventDataField(data, 'ScriptBlockText');
    const scriptPath = getEventDataField(data, 'Path');

    return {
      timestamp: new Date(system.TimeCreated.$.SystemTime),
      eventType: 'script_block',
      processName: 'powershell.exe',
      commandLine: scriptPath || '',
      pid: parseInt(system.Execution ? system.Execution.$.ProcessID : '0', 10) || 0,
      parentProcessName: '',
      parentCommandLine: '',
      parentPid: 0,
      user: system.Security ? (system.Security.$.UserID || '') : '',
      hash: { sha256: '' },
      scriptBlockText: scriptText,
      eventRecordId: system.EventRecordID || ''
    };
  } catch (err) {
    console.error('[EventLogReader] Failed to normalize PS ScriptBlock event:', err.message);
    return null;
  }
}

/**
 * Normalize a PowerShell Event ID 4103 (Module Logging) event.
 */
function normalizePSModuleLog(parsed) {
  try {
    const system = parsed.Event.System;
    const eventData = parsed.Event.EventData;
    const data = eventData ? eventData.Data : [];

    const payload = getEventDataField(data, 'Payload');
    const commandLine = getEventDataField(data, 'CommandLine') || payload;

    return {
      timestamp: new Date(system.TimeCreated.$.SystemTime),
      eventType: 'module_log',
      processName: 'powershell.exe',
      commandLine: commandLine,
      pid: parseInt(system.Execution ? system.Execution.$.ProcessID : '0', 10) || 0,
      parentProcessName: '',
      parentCommandLine: '',
      parentPid: 0,
      user: system.Security ? (system.Security.$.UserID || '') : '',
      hash: { sha256: '' },
      scriptBlockText: payload || '',
      eventRecordId: system.EventRecordID || ''
    };
  } catch (err) {
    console.error('[EventLogReader] Failed to normalize PS Module event:', err.message);
    return null;
  }
}

// ── Main Reader Functions ──────────────────────────────────────────────────

/**
 * Read and normalize Sysmon Process Create events (Event ID 1).
 *
 * @param {string|null} sinceTimestamp - ISO timestamp to read events after (null = all)
 * @returns {Promise<{events: Object[], latestTimestamp: string|null}>}
 */
async function readSysmonEvents(sinceTimestamp) {
  const channel = 'Microsoft-Windows-Sysmon/Operational';
  const query = buildXPathQuery([1], sinceTimestamp);

  let rawXml;
  try {
    rawXml = await queryEventLog(channel, query);
  } catch (err) {
    console.error('[EventLogReader] Sysmon query failed:', err.message);
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  if (!rawXml || rawXml.trim().length === 0) {
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  // wevtutil outputs multiple <Event> elements without a root wrapper.
  // Wrap in a root element to make it valid XML for parsing.
  const wrappedXml = `<Events>${rawXml}</Events>`;

  let parsed;
  try {
    parsed = await parseXML(wrappedXml);
  } catch (err) {
    console.error('[EventLogReader] Failed to parse Sysmon XML:', err.message);
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  if (!parsed || !parsed.Events || !parsed.Events.Event) {
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  const rawEvents = Array.isArray(parsed.Events.Event)
    ? parsed.Events.Event
    : [parsed.Events.Event];

  const events = [];
  let latestTimestamp = sinceTimestamp;

  for (const rawEvent of rawEvents) {
    const normalized = normalizeSysmonEvent({ Event: rawEvent });
    if (normalized) {
      events.push(normalized);
      // Track the latest timestamp for next poll
      const eventTime = normalized.timestamp.toISOString();
      if (!latestTimestamp || eventTime > latestTimestamp) {
        latestTimestamp = eventTime;
      }
    }
  }

  return { events, latestTimestamp };
}

/**
 * Read and normalize PowerShell logging events (Event IDs 4104, 4103).
 *
 * @param {string|null} sinceTimestamp - ISO timestamp to read events after (null = all)
 * @returns {Promise<{events: Object[], latestTimestamp: string|null}>}
 */
async function readPowerShellEvents(sinceTimestamp) {
  const channel = 'Microsoft-Windows-PowerShell/Operational';
  const query = buildXPathQuery([4104, 4103], sinceTimestamp);

  let rawXml;
  try {
    rawXml = await queryEventLog(channel, query);
  } catch (err) {
    console.error('[EventLogReader] PowerShell query failed:', err.message);
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  if (!rawXml || rawXml.trim().length === 0) {
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  const wrappedXml = `<Events>${rawXml}</Events>`;

  let parsed;
  try {
    parsed = await parseXML(wrappedXml);
  } catch (err) {
    console.error('[EventLogReader] Failed to parse PowerShell XML:', err.message);
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  if (!parsed || !parsed.Events || !parsed.Events.Event) {
    return { events: [], latestTimestamp: sinceTimestamp };
  }

  const rawEvents = Array.isArray(parsed.Events.Event)
    ? parsed.Events.Event
    : [parsed.Events.Event];

  const events = [];
  let latestTimestamp = sinceTimestamp;

  for (const rawEvent of rawEvents) {
    const eventId = rawEvent.System
      ? (rawEvent.System.EventID && typeof rawEvent.System.EventID === 'object'
        ? rawEvent.System.EventID._
        : rawEvent.System.EventID)
      : null;

    let normalized = null;
    if (eventId == 4104) {
      normalized = normalizePSScriptBlock({ Event: rawEvent });
    } else if (eventId == 4103) {
      normalized = normalizePSModuleLog({ Event: rawEvent });
    }

    if (normalized) {
      events.push(normalized);
      const eventTime = normalized.timestamp.toISOString();
      if (!latestTimestamp || eventTime > latestTimestamp) {
        latestTimestamp = eventTime;
      }
    }
  }

  return { events, latestTimestamp };
}

module.exports = {
  readSysmonEvents,
  readPowerShellEvents,
  buildXPathQuery,
  queryEventLog
};
