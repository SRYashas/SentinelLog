/**
 * SentinelLog — Origin Resolver
 * ================================
 * Determines HOW and WHY a process was launched by cross-referencing:
 *   1. Registry Run/RunOnce keys (HKCU & HKLM)
 *   2. Startup folder contents (user & all-users)
 *   3. Scheduled Tasks
 *   4. Windows Services
 *   5. Parent process chain (explorer.exe = user interactive)
 *
 * If none of these explain the process origin, it's marked as "unknown" —
 * which is the MOST VALUABLE signal for the user (unexplained popups are
 * the whole point of this project).
 *
 * Results are cached with a configurable TTL to avoid querying the system
 * on every single event. The cache is refreshed periodically.
 */

const { execFile, exec } = require('child_process');
const path = require('path');

// ── Cache Configuration ────────────────────────────────────────────────────

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

let cache = {
  registryEntries: [],
  startupEntries: [],
  scheduledTasks: [],
  services: [],
  lastRefresh: 0
};

// ── System Query Functions ─────────────────────────────────────────────────

/**
 * Query registry Run/RunOnce keys for auto-start entries.
 * Checks both HKCU and HKLM variants.
 */
function queryRegistryRunKeys() {
  const keys = [
    'HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run',
    'HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce',
    'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run',
    'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce',
    'HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run',
    'HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\RunOnce'
  ];

  const promises = keys.map(key => {
    return new Promise((resolve) => {
      execFile('reg', ['query', key], { timeout: 10000 }, (error, stdout) => {
        if (error || !stdout) {
          resolve([]);
          return;
        }
        // Parse reg query output: each entry is "    ValueName    REG_SZ    CommandLine"
        const entries = [];
        const lines = stdout.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('HKEY_')) continue;
          // Match: name    REG_TYPE    value
          const match = trimmed.match(/^(.+?)\s+(REG_\w+)\s+(.+)$/);
          if (match) {
            entries.push({
              key: key,
              name: match[1].trim(),
              value: match[3].trim(),
              // Extract the executable name from the command line
              executable: extractExeFromCommand(match[3].trim())
            });
          }
        }
        resolve(entries);
      });
    });
  });

  return Promise.all(promises).then(results => results.flat());
}

/**
 * Query startup folder contents (user and all-users).
 */
function queryStartupFolders() {
  return new Promise((resolve) => {
    // Get the startup folder paths via environment variables / known paths
    const userStartup = path.join(
      process.env.APPDATA || 'C:\\Users\\Default\\AppData\\Roaming',
      'Microsoft\\Windows\\Start Menu\\Programs\\Startup'
    );
    const allUsersStartup = path.join(
      process.env.PROGRAMDATA || 'C:\\ProgramData',
      'Microsoft\\Windows\\Start Menu\\Programs\\Startup'
    );

    const folders = [userStartup, allUsersStartup];
    const entries = [];

    let pending = folders.length;
    for (const folder of folders) {
      exec(`dir /b "${folder}" 2>nul`, { timeout: 10000 }, (error, stdout) => {
        if (!error && stdout) {
          const files = stdout.split('\n').filter(f => f.trim().length > 0);
          for (const file of files) {
            entries.push({
              folder: folder,
              filename: file.trim(),
              executable: file.trim().toLowerCase().replace('.lnk', '').replace('.exe', '')
            });
          }
        }
        pending--;
        if (pending === 0) resolve(entries);
      });
    }
  });
}

/**
 * Query scheduled tasks via schtasks.
 */
function queryScheduledTasks() {
  return new Promise((resolve) => {
    exec('schtasks /query /fo CSV /v /nh', { timeout: 30000, maxBuffer: 5 * 1024 * 1024 }, (error, stdout) => {
      if (error || !stdout) {
        resolve([]);
        return;
      }

      const entries = [];
      const lines = stdout.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('"HostName"')) continue;

        // CSV format: "HostName","TaskName","Next Run","Status","Logon Mode","Last Run","Last Result","Author","Task To Run",...
        // We need TaskName (index 1) and Task To Run (index 8)
        try {
          const fields = parseCSVLine(trimmed);
          if (fields.length >= 9) {
            const taskName = fields[1] || '';
            const taskToRun = fields[8] || '';
            if (taskToRun && taskToRun !== 'N/A') {
              entries.push({
                taskName: taskName,
                command: taskToRun,
                executable: extractExeFromCommand(taskToRun)
              });
            }
          }
        } catch (e) {
          // Skip malformed lines
        }
      }
      resolve(entries);
    });
  });
}

/**
 * Query Windows services via sc query.
 */
function queryServices() {
  return new Promise((resolve) => {
    exec('sc query state= all', { timeout: 30000, maxBuffer: 5 * 1024 * 1024 }, (error, stdout) => {
      if (error || !stdout) {
        resolve([]);
        return;
      }

      const entries = [];
      const blocks = stdout.split('\n\n');
      for (const block of blocks) {
        const nameMatch = block.match(/SERVICE_NAME:\s*(.+)/);
        const displayMatch = block.match(/DISPLAY_NAME:\s*(.+)/);
        if (nameMatch) {
          entries.push({
            serviceName: nameMatch[1].trim(),
            displayName: displayMatch ? displayMatch[1].trim() : '',
            executable: nameMatch[1].trim().toLowerCase()
          });
        }
      }
      resolve(entries);
    });
  });
}

// ── Helper Functions ───────────────────────────────────────────────────────

/**
 * Extract executable name from a command line string.
 * e.g., "C:\Program Files\App\app.exe --flag" → "app.exe"
 * e.g., '"C:\path\app.exe" -arg' → "app.exe"
 */
function extractExeFromCommand(cmdLine) {
  if (!cmdLine) return '';
  // Remove quotes and extract the first path-like segment
  let cleaned = cmdLine.replace(/^["']/, '').replace(/["'].*$/, '');
  if (!cleaned) cleaned = cmdLine;
  // Get the basename
  const basename = path.basename(cleaned.split(/\s+/)[0]);
  return basename.toLowerCase();
}

/**
 * Simple CSV line parser that handles quoted fields.
 */
function parseCSVLine(line) {
  const fields = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      fields.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  fields.push(current.trim());
  return fields;
}

// ── Cache Refresh ──────────────────────────────────────────────────────────

/**
 * Refresh the system lookup cache if it's stale.
 * This runs all 4 system queries in parallel.
 */
async function refreshCacheIfNeeded() {
  const now = Date.now();
  if (now - cache.lastRefresh < CACHE_TTL_MS) {
    return; // Cache is still fresh
  }

  console.log('[OriginResolver] Refreshing system lookup cache...');

  try {
    const [registry, startup, tasks, services] = await Promise.all([
      queryRegistryRunKeys(),
      queryStartupFolders(),
      queryScheduledTasks(),
      queryServices()
    ]);

    cache = {
      registryEntries: registry,
      startupEntries: startup,
      scheduledTasks: tasks,
      services: services,
      lastRefresh: now
    };

    console.log(`[OriginResolver] Cache refreshed: ${registry.length} registry, ${startup.length} startup, ${tasks.length} tasks, ${services.length} services`);
  } catch (err) {
    console.error('[OriginResolver] Cache refresh failed:', err.message);
    // Keep stale cache rather than having no data
    cache.lastRefresh = now - CACHE_TTL_MS + 30000; // Retry in 30s
  }
}

// ── Origin Resolution ──────────────────────────────────────────────────────

/**
 * Resolve the origin of a process creation event.
 *
 * Cross-references the process name and command line against:
 *   1. Registry Run/RunOnce keys
 *   2. Startup folder contents
 *   3. Scheduled Tasks
 *   4. Windows Services
 *   5. Parent process chain
 *
 * Returns: { resolved: Boolean, source: String, detail: String }
 *
 * @param {Object} event - Normalized event object with processName, commandLine,
 *                         parentProcessName, parentCommandLine
 * @returns {Object} Origin resolution result
 */
async function resolveOrigin(event) {
  await refreshCacheIfNeeded();

  const procName = (event.processName || '').toLowerCase();
  const cmdLine = (event.commandLine || '').toLowerCase();
  const parentName = (event.parentProcessName || '').toLowerCase();

  // ── Check 1: Registry Run/RunOnce keys ───────────────────────────────
  // If the process executable matches an auto-run registry entry
  for (const entry of cache.registryEntries) {
    if (entry.executable === procName ||
        cmdLine.includes(entry.value.toLowerCase())) {
      return {
        resolved: true,
        source: 'registry_run',
        detail: `${entry.key}\\${entry.name} → ${entry.value}`
      };
    }
  }

  // ── Check 2: Startup folder ──────────────────────────────────────────
  // If the process matches a startup folder shortcut
  for (const entry of cache.startupEntries) {
    if (procName.includes(entry.executable) ||
        entry.filename.toLowerCase().includes(procName.replace('.exe', ''))) {
      return {
        resolved: true,
        source: 'startup_folder',
        detail: `${entry.folder}\\${entry.filename}`
      };
    }
  }

  // ── Check 3: Scheduled Tasks ─────────────────────────────────────────
  // If the process matches a scheduled task command
  for (const entry of cache.scheduledTasks) {
    if (entry.executable === procName ||
        entry.command.toLowerCase().includes(procName)) {
      return {
        resolved: true,
        source: 'scheduled_task',
        detail: `Task: ${entry.taskName} → ${entry.command}`
      };
    }
  }

  // ── Check 4: Windows Services ────────────────────────────────────────
  // If the process matches a known service
  for (const entry of cache.services) {
    if (entry.executable === procName ||
        entry.serviceName.toLowerCase() === procName.replace('.exe', '')) {
      return {
        resolved: true,
        source: 'service',
        detail: `Service: ${entry.serviceName} (${entry.displayName})`
      };
    }
  }

  // ── Check 5: Parent process chain ────────────────────────────────────
  // If the parent is explorer.exe, the user likely launched it interactively
  if (parentName === 'explorer.exe') {
    return {
      resolved: true,
      source: 'user_interactive',
      detail: 'Launched from Windows Explorer (user double-click or Start Menu)'
    };
  }

  // If parent is svchost.exe, it's likely service-spawned
  if (parentName === 'svchost.exe' || parentName === 'services.exe') {
    return {
      resolved: true,
      source: 'service',
      detail: `Spawned by system service host (parent: ${event.parentProcessName})`
    };
  }

  // If parent is cmd.exe or powershell.exe spawned from explorer, it's user interactive
  if ((parentName === 'cmd.exe' || parentName === 'powershell.exe' || parentName === 'pwsh.exe') &&
      event.parentCommandLine && !event.parentCommandLine.toLowerCase().includes('-windowstyle hidden')) {
    return {
      resolved: true,
      source: 'user_interactive',
      detail: `Launched from ${event.parentProcessName} (interactive session)`
    };
  }

  // ── No match found — this is UNKNOWN origin ─────────────────────────
  // This is the most interesting case! An unexplained process popup.
  return {
    resolved: false,
    source: 'unknown',
    detail: `No known trigger found. Parent: ${event.parentProcessName || 'N/A'} (PID: ${event.parentPid || 'N/A'})`
  };
}

/**
 * Force-refresh the origin cache (useful for testing or manual triggers).
 */
async function forceRefreshCache() {
  cache.lastRefresh = 0;
  await refreshCacheIfNeeded();
}

module.exports = {
  resolveOrigin,
  refreshCacheIfNeeded,
  forceRefreshCache
};
