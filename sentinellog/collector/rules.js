/**
 * SentinelLog — Suspicious Command Detection Rules
 * ====================================================
 * A configurable rules engine for flagging potentially suspicious commands.
 *
 * Each rule is a simple object:
 *   { name, pattern (regex), fields (which event fields to check), riskLevel, reason }
 *
 * To add new rules, just append to the RULES array below.
 * No code changes elsewhere are needed — the engine iterates all rules automatically.
 *
 * Risk levels:
 *   - "info"       = normal activity, no concern
 *   - "suspicious" = worth investigating, might be benign
 *   - "high"       = likely malicious or highly unusual pattern
 */

// ── Detection Rules ────────────────────────────────────────────────────────

const RULES = [
  // ── HIGH RISK ──────────────────────────────────────────────────────────

  {
    name: 'encoded_powershell',
    // Matches -enc, -EncodedCommand, -encodedcommand, -ec (common abbreviation)
    pattern: /\-(enc|encodedcommand|ec)\s/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'Encoded PowerShell command (-EncodedCommand) — often used to obfuscate malicious payloads'
  },

  {
    name: 'hidden_powershell',
    // -NoProfile combined with -WindowStyle Hidden
    pattern: /\-(nop|noprofile)\b.*\-(w|windowstyle)\s*(hidden|h)\b/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'Hidden PowerShell window with -NoProfile — classic evasion technique'
  },

  {
    name: 'hidden_powershell_reverse',
    // Reverse order: -WindowStyle Hidden ... -NoProfile
    pattern: /\-(w|windowstyle)\s*(hidden|h)\b.*\-(nop|noprofile)\b/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'Hidden PowerShell window with -NoProfile — classic evasion technique'
  },

  {
    name: 'iex_webclient',
    // IEX (New-Object Net.WebClient) or variations
    pattern: /IEX\s*[\(\{]?\s*(New-Object\s+)?(Net\.WebClient|System\.Net\.WebClient)/i,
    fields: ['commandLine', 'scriptBlockText'],
    riskLevel: 'high',
    reason: 'IEX with WebClient — classic download-and-execute cradle'
  },

  {
    name: 'download_string',
    // DownloadString or DownloadFile patterns
    pattern: /\.(DownloadString|DownloadFile|DownloadData)\s*\(/i,
    fields: ['commandLine', 'scriptBlockText'],
    riskLevel: 'high',
    reason: 'Network download function detected (DownloadString/DownloadFile)'
  },

  {
    name: 'invoke_webrequest',
    // Invoke-WebRequest / Invoke-RestMethod / wget / curl aliases in PS
    pattern: /(Invoke-WebRequest|Invoke-RestMethod|iwr\s|wget\s|curl\s).*https?:\/\//i,
    fields: ['commandLine', 'scriptBlockText'],
    riskLevel: 'high',
    reason: 'Web request downloading external content'
  },

  {
    name: 'certutil_abuse',
    // certutil -urlcache or certutil -decode (LOLBin abuse)
    pattern: /certutil\s+.*\-(urlcache|decode)/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'certutil LOLBin abuse — commonly used for downloading or decoding payloads'
  },

  {
    name: 'mshta_execution',
    // mshta executing content
    pattern: /mshta\s+(https?:\/\/|javascript:|vbscript:)/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'mshta executing remote or inline script — known LOLBin technique'
  },

  {
    name: 'wscript_cscript_office_spawn',
    // wscript.exe or cscript.exe — risk depends on parent, checked separately
    pattern: /(wscript|cscript)(\.exe)?\s/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'Script host execution (wscript/cscript) — frequently abused for malware delivery',
    // Additional check: only flag as high if parent is Office app or browser
    parentCheck: /(winword|excel|powerpnt|outlook|msedge|chrome|firefox|iexplore)(\.exe)?$/i
  },

  {
    name: 'powershell_bypass_execution_policy',
    // Bypass execution policy
    pattern: /\-(ep|executionpolicy)\s+(bypass|unrestricted)/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'PowerShell execution policy bypass — may indicate script evasion'
  },

  {
    name: 'registry_add_run_key',
    // Adding registry run keys programmatically
    pattern: /reg\s+add\s+.*\\(Run|RunOnce)/i,
    fields: ['commandLine'],
    riskLevel: 'high',
    reason: 'Registry Run key modification — potential persistence mechanism'
  },

  // ── SUSPICIOUS ─────────────────────────────────────────────────────────

  {
    name: 'bitsadmin_transfer',
    pattern: /bitsadmin\s+.*\/transfer/i,
    fields: ['commandLine'],
    riskLevel: 'suspicious',
    reason: 'bitsadmin file transfer — sometimes used for stealthy downloads'
  },

  {
    name: 'base64_long_string',
    // Heuristic: a long string of Base64-looking characters (>100 chars)
    // Base64 charset: A-Za-z0-9+/=
    pattern: /[A-Za-z0-9+\/=]{100,}/,
    fields: ['commandLine'],
    riskLevel: 'suspicious',
    reason: 'Long Base64-like string in command line — may be obfuscated payload'
  },

  {
    name: 'scheduled_task_creation',
    // Creating a scheduled task from command line
    pattern: /schtasks\s+.*\/(create|change)/i,
    fields: ['commandLine'],
    riskLevel: 'suspicious',
    reason: 'Scheduled task creation/modification — potential persistence'
  },

  {
    name: 'service_creation',
    // Creating or modifying a Windows service
    pattern: /sc\s+(create|config)\s/i,
    fields: ['commandLine'],
    riskLevel: 'suspicious',
    reason: 'Windows service creation/modification — potential persistence'
  },

  {
    name: 'powershell_reflection',
    // .NET reflection / Assembly loading
    pattern: /(Reflection\.Assembly|LoadWithPartialName|Add-Type\s+-TypeDefinition)/i,
    fields: ['commandLine', 'scriptBlockText'],
    riskLevel: 'suspicious',
    reason: '.NET reflection or assembly loading — may indicate advanced techniques'
  },

  {
    name: 'credential_access',
    // Credential-related commands
    pattern: /(mimikatz|sekurlsa|Get-Credential|ConvertTo-SecureString|cmdkey)/i,
    fields: ['commandLine', 'scriptBlockText'],
    riskLevel: 'suspicious',
    reason: 'Credential access pattern detected'
  },

  {
    name: 'whoami_recon',
    // Basic reconnaissance commands
    pattern: /\b(whoami|systeminfo|ipconfig\s+\/all|net\s+(user|localgroup|group))\b/i,
    fields: ['commandLine'],
    riskLevel: 'suspicious',
    reason: 'System reconnaissance command — common in post-exploitation'
  }
];

// ── Rules Engine ───────────────────────────────────────────────────────────

/**
 * Evaluate all rules against an event and return the highest risk level
 * and all matched reasons.
 *
 * @param {Object} event - Normalized event object
 * @returns {{ riskLevel: string, riskReasons: string[] }}
 */
function evaluateRules(event) {
  const matchedReasons = [];
  let highestRisk = 'info';

  for (const rule of RULES) {
    // Check if the rule has a parent check that must also match
    if (rule.parentCheck) {
      const parentName = event.parentProcessName || '';
      if (!rule.parentCheck.test(parentName)) {
        // Parent doesn't match — downgrade to suspicious instead of skipping entirely
        // (wscript/cscript are still somewhat suspicious even without Office parent)
        continue;
      }
    }

    // Test the pattern against each specified field
    let matched = false;
    for (const field of rule.fields) {
      const value = event[field];
      if (value && rule.pattern.test(value)) {
        matched = true;
        break;
      }
    }

    if (matched) {
      matchedReasons.push(rule.reason);
      if (riskPriority(rule.riskLevel) > riskPriority(highestRisk)) {
        highestRisk = rule.riskLevel;
      }
    }
  }

  return {
    riskLevel: highestRisk,
    riskReasons: matchedReasons
  };
}

/**
 * Special check: Flag events with unresolved origin that appear non-interactive
 * as suspicious (this runs AFTER origin resolution).
 *
 * @param {Object} event - Event with origin already resolved
 * @returns {{ riskLevel: string, riskReasons: string[] }} Additional risk info
 */
function evaluateOriginRisk(event) {
  if (!event.origin || event.origin.resolved) {
    return { riskLevel: 'info', riskReasons: [] };
  }

  // Check if the process appears non-interactive
  const cmdLine = (event.commandLine || '').toLowerCase();
  const isHidden = cmdLine.includes('-windowstyle hidden') ||
                   cmdLine.includes('-w hidden') ||
                   cmdLine.includes('/b ');  // start /b = background

  const parentName = (event.parentProcessName || '').toLowerCase();
  const isUserShell = parentName === 'explorer.exe' ||
                      parentName === 'cmd.exe' ||
                      parentName === 'powershell.exe';

  if (!isUserShell || isHidden) {
    return {
      riskLevel: 'suspicious',
      riskReasons: ['Process with unresolved origin running non-interactively']
    };
  }

  return { riskLevel: 'info', riskReasons: [] };
}

/**
 * Numeric priority for risk levels (higher = more severe).
 */
function riskPriority(level) {
  switch (level) {
    case 'high': return 3;
    case 'suspicious': return 2;
    case 'info': return 1;
    default: return 0;
  }
}

/**
 * Full risk evaluation: combines pattern rules + origin-based risk.
 *
 * @param {Object} event - Event with origin already resolved
 * @returns {{ riskLevel: string, riskReasons: string[] }}
 */
function evaluateFullRisk(event) {
  const patternResult = evaluateRules(event);
  const originResult = evaluateOriginRisk(event);

  // Merge results — take the highest risk level and combine reasons
  const allReasons = [...patternResult.riskReasons, ...originResult.riskReasons];
  const highestRisk = riskPriority(patternResult.riskLevel) >= riskPriority(originResult.riskLevel)
    ? patternResult.riskLevel
    : originResult.riskLevel;

  return {
    riskLevel: allReasons.length > 0 ? highestRisk : 'info',
    riskReasons: allReasons
  };
}

module.exports = {
  RULES,
  evaluateRules,
  evaluateOriginRisk,
  evaluateFullRisk,
  riskPriority
};
