# SentinelLog — Offline Windows Process & Console Activity Monitor

SentinelLog is a **fully offline, local-only** security monitoring tool for Windows. It watches for command-line/PowerShell windows that pop up on the system (whether user-initiated, triggered by startup programs, scheduled tasks, or unknown sources), logs full command lines and process lineage, captures PowerShell session execution, stores everything in a local database, and presents it through a local web dashboard.

---

## 🔒 100% Offline & Localhost Guarantee

- **Zero external network calls**: No CDNs, no cloud database, no telemetry, no auto-update checks.
- **Local dependencies only**: Tailwind CSS v4, Inter font, Lucide icons, and Recharts charting library are all bundled locally via npm.
- **Local binding**: Express API server binds strictly to `127.0.0.1` (never `0.0.0.0`).
- **Verifiable codebase**: Run `grep -r "https\?://" --exclude-dir=node_modules` across the project (outside of local setup documentation URLs) to verify zero network requests.

---

## 🎯 Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               Windows Event Sources                    │
│  Sysmon (Event ID 1)   PowerShell (Event ID 4104/4103) │
└───────────────────────────┬────────────────────────────┘
                            │ (wevtutil XML poll)
                            ▼
┌────────────────────────────────────────────────────────┐
│            SentinelLog Collector Service               │
│  - Event Log Poller & Normalizer                       │
│  - Origin Resolver (Registry/Startup/Task/Service)     │
│  - Suspicious Rules Engine                             │
└───────────────────────────┬────────────────────────────┘
                            │ (Mongoose)
                            ▼
┌────────────────────────────────────────────────────────┐
│             Local MongoDB Community Server             │
│              mongodb://127.0.0.1:27017                  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Express API + Static React Server          │
│                   http://127.0.0.1:3000                │
└────────────────────────────────────────────────────────┘
```

---

## ⚠️ Important System Caveats & Requirements

### 1. `cmd.exe` Limitation Note
`cmd.exe` does not feature built-in session transcription. SentinelLog captures `cmd.exe` activity at the **process level** (every command run via `cmd.exe` appears as its own process-creation event with full command line parameters captured via Sysmon, e.g. `cmd /c whoami`). Interactive internal keystrokes typed inside an open `cmd.exe` prompt are NOT captured unless manual history tools are run. This is an intentional design boundary — no custom keylogger hooks are used.

### 2. Manual Sysmon Placement (Offline Requirement)
In compliance with the offline specification, SentinelLog does **NOT** download Sysmon automatically from the web.
1. Download `Sysmon` from Microsoft Sysinternals on an internet-connected machine.
2. Place `Sysmon64.exe` inside the `/tools` directory:
   `d:\log extractor\sentinellog\tools\Sysmon64.exe`

### 3. Local MongoDB Service
MongoDB Community Server must be pre-installed and running locally at `mongodb://127.0.0.1:27017`.

---

## 🛠️ Step-by-Step Setup Guide

### Step 1: Place Sysmon Binary
Copy `Sysmon64.exe` to `sentinellog/tools/Sysmon64.exe`.

### Step 2: Enable System Event Logging (Run as Admin)
Open PowerShell as Administrator and execute:

```powershell
# 1. Install & Configure Sysmon for Event ID 1 (Process Create)
Set-ExecutionPolicy Bypass -Scope Process -Force
.\setup\install-sysmon.ps1

# 2. Enable PowerShell Script Block, Module Logging & Flat Transcripts
.\setup\powershell-logging.ps1
```

### Step 3: Install Local Node Dependencies
From the project root folder:

```bash
npm install
```
*(This automatically runs `npm install` inside server, collector, and dashboard directories)*

### Step 4: Build the Dashboard & Start the Server

```bash
# Build React dashboard static bundle
npm run build

# Start Express server (serves dashboard on http://127.0.0.1:3000)
npm run start
```

### Step 5: Start the Collector Service

You can run the collector in the background during development or install it as a native Windows service:

**Development Mode (Foreground):**
```bash
npm run collector
```

**Production Mode (Windows Background Service):**
Run Command Prompt / PowerShell as **Administrator**:
```bash
npm run install-service
```
This registers "SentinelLog Collector" as a Windows service configured to start automatically on system boot.

---

## 🧠 Smart Core Logic Overview

### 1. Origin Resolver (`collector/originResolver.js`)
When a process is spawned, SentinelLog attempts to explain *why* it opened by cross-referencing:
1. **Registry Run / RunOnce Keys**: `HKCU\...\Run`, `HKLM\...\Run`, etc.
2. **Startup Folders**: `shell:startup` and All Users startup folder shortcuts.
3. **Scheduled Tasks**: Parsing `schtasks /query /fo CSV`.
4. **Windows Services**: Querying `sc query state= all`.
5. **Parent Process Chain**: Checking if spawned interactively via `explorer.exe`.

If none of these sources explain the trigger, the process is tagged as `origin.resolved: false` (`source: "unknown"`). These unexplained popups are flagged prominently in the UI.

### 2. Suspicious Command Detection Rules (`collector/rules.js`)
Commands and script blocks are passed through a rules engine evaluating pattern checks:
- **Base64 PowerShell**: `-enc` / `-EncodedCommand` (High Risk)
- **Evasion Flags**: `-NoProfile` + `-WindowStyle Hidden` (High Risk)
- **Download Cradles**: `IEX (New-Object Net.WebClient)` or `.DownloadString()` (High Risk)
- **LOLBin Abuse**: `certutil -urlcache` / `certutil -decode` (High Risk)
- **Office / Browser Spawning**: `mshta`, `wscript`, `cscript` (High Risk)
- **BITS Transfer**: `bitsadmin /transfer` (Suspicious)
- **Unresolved Background Popups**: Process with unresolved origin running non-interactively (Suspicious)

---

## 🌐 Dashboard Features (`http://127.0.0.1:3000`)

1. **Overview Dashboard**: Stat cards, 24-hour event frequency area chart, risk level distribution pie chart, and top unexplained processes.
2. **Live Timeline**: Real-time reverse-chronological feed with auto-polling (5s interval).
3. **Unknown Origins View**: Filtered view surfacing unexplained process creation popups.
4. **Suspicious Activity View**: Filtered feed of high-risk and suspicious rule triggers.
5. **Process Explorer**: Grouping by process name with parent-child process lineage trees.
6. **Single Event Deep Inspection**: Full unredacted command lines, script block contents, process lineage, SHA256 hashes, and copy controls.
