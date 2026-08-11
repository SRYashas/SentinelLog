# SentinelLog — User Guide & Operational Manual

A comprehensive, step-by-step guide on how to configure, run, navigate, and interpret process activity using **SentinelLog**.

---

## 📋 Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Initial System Setup (One-Time)](#2-initial-system-setup-one-time)
3. [Starting SentinelLog](#3-starting-sentinellog)
4. [Navigating the Dashboard](#4-navigating-the-dashboard)
5. [Understanding Event Origins & Trigger Resolution](#5-understanding-event-origins--trigger-resolution)
6. [Suspicious Command Detection Rules](#6-suspicious-command-detection-rules)
7. [Running as a Permanent Windows Background Service](#7-running-as-a-permanent-windows-background-service)
8. [Troubleshooting & FAQs](#8-troubleshooting--faqs)

---

## 1. Prerequisites

Before using SentinelLog, ensure your Windows machine has:
- **Windows 10 / 11** (64-bit)
- **Node.js 18+** installed
- **Sysmon64.exe** placed in `sentinellog/tools/Sysmon64.exe` *(Sysinternals binary — not auto-downloaded for offline compliance)*
- **Administrative Privileges** for initial registry & service configuration

---

## 2. Initial System Setup (One-Time)

To allow SentinelLog to capture full process creation lineage and internal PowerShell script execution, run the setup scripts.

### Step 2.1: Enable Sysmon Event Logging
Open **PowerShell as Administrator** in the project folder (`sentinellog`):

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\setup\install-sysmon.ps1
```
> **What this does:** Configures Sysmon to log Event ID 1 (Process Creation) with unredacted command line arguments, parent process PIDs, user context, and SHA256 hashes into the Windows Event Log (`Microsoft-Windows-Sysmon/Operational`).

### Step 2.2: Enable PowerShell Logging & Transcription
In the same elevated PowerShell window:

```powershell
.\setup\powershell-logging.ps1
```
> **What this does:** Enables Script Block Logging (Event ID 4104), Module Logging (Event ID 4103), and flat-file transcript backups in `C:\SentinelLog\transcripts`.

---

## 3. Starting SentinelLog

SentinelLog includes an embedded auto-starting database helper, an Express API server, and a background log collector.

### Option A: Native Windows Desktop App (No Browser Needed! 🎉)

Launch SentinelLog as a standalone Windows desktop app with its own native window and system tray icon:

```bash
npm run app
```
*   Opens a native Windows app window.
*   Minimizes to the Windows System Tray near the clock.
*   No browser needed!

### Option B: Standard Web Browser Mode

```bash
# 1. Start the API Server & Dashboard
npm start

# 2. Start the Event Log Collector (in a second terminal)
npm run collector
```
*The server will start listening at `http://127.0.0.1:3000` and automatically launch a local MongoDB instance if one isn't already running.*

Open a second terminal window in `sentinellog` to run the Collector:

```bash
# 2. Start the Event Log Collector
npm run collector
```
*The collector immediately begins polling Windows Event Logs every 5 seconds, enriching process creation data, and inserting logs into MongoDB.*

### Option B: Accessing the Web Dashboard
Open your web browser and navigate to:
👉 **[http://127.0.0.1:3000](http://127.0.0.1:3000)**

---

## 4. Navigating the Dashboard

The SentinelLog dashboard features dark-mode styling with 5 primary views accessible from the sidebar.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SENTINELLOG DASHBOARD                           │
├───────────────┬────────────────────────────────────────────────────────┤
│ 📊 Overview   │ Real-time stats, 24h event area chart, risk pie chart   │
│ ⚡ Timeline   │ Reverse-chronological live event feed with 5s polling  │
│ ❓ Unknown    │ Dedicated view of unexplained process creation popups  │
│ 🚨 Suspicious │ Filtered list of high-risk and suspicious command lines│
│ 🌿 Processes  │ Process execution frequency and parent-child tree      │
└───────────────┴────────────────────────────────────────────────────────┘
```

### View 1: System Activity Overview (`/`)
- **Metric Cards**: Total 24h event count, unexplained popups, high-risk flags, and suspicious commands.
- **Event Activity Chart**: Area graph showing hourly process execution spikes over the past 24 hours.
- **Risk Breakdown**: Donut chart displaying the ratio of Info vs. Suspicious vs. High Risk commands.
- **Latest Process Feed**: Click any row to expand and inspect full command line parameters.

### View 2: Live Event Timeline (`/timeline`)
- Shows a live feed of all process creations (`process_create`), PowerShell script blocks (`script_block`), and module logs (`module_log`).
- **Live Polling Toggle**: Pause/resume real-time 5-second polling.
- **Search & Filter Bar**:
  - Filter by keyword in command line or script body.
  - Filter by risk level (*Info*, *Suspicious*, *High Risk*).
  - Filter by trigger origin (*Registry Run*, *Startup Folder*, *Scheduled Task*, *Service*, *Interactive*, *Unknown*).
  - Filter by process name (e.g. `cmd.exe`, `powershell.exe`).

### View 3: Unknown / Unexplained Origins (`/unresolved`)
- **This is the primary view for finding unexpected popups!**
- Lists processes launched on the system where no Registry Run key, Startup folder shortcut, Scheduled Task, or Windows Service could explain why it started.

### View 4: Suspicious Activity (`/suspicious`)
- Displays processes and scripts flagged by the built-in detection rules engine.
- Every entry shows the exact matched security rule reasons (e.g., *-EncodedCommand detected*, *IEX download cradle*, *Certutil abuse*).

### View 5: Process Explorer & Lineage (`/processes`)
- Groups event activity by executable name.
- Select a process (e.g. `powershell.exe`) to view its **Parent-Child Process Lineage Tree** (showing which parent processes spawned it and how many times).

### View 6: Deep Dive Event Inspection (`/events/:id`)
- Click **"View Full Event Inspection"** on any row to open full-screen inspection:
  - Unredacted full command line with one-click **Copy to Clipboard** button.
  - Complete PowerShell Script Block content (for Event ID 4104).
  - Parent process executable path, PID, and parent command line.
  - User context (e.g. `NT AUTHORITY\SYSTEM` or `DOMAIN\User`).
  - SHA256 executable hash.

---

## 5. Understanding Event Origins & Trigger Resolution

When a process opens, SentinelLog runs an **Origin Resolver** (`collector/originResolver.js`) that checks 5 lookup sources:

| Origin Badge | Meaning / Trigger Source |
| :--- | :--- |
| <span style="color:#c084fc font-weight:bold">Registry Run</span> | Process matched an auto-start key in `HKCU\...\Run` or `HKLM\...\Run`. |
| <span style="color:#60a5fa font-weight:bold">Startup Folder</span> | Process matched a shortcut file in `shell:startup` or `ProgramData\Startup`. |
| <span style="color:#34d399 font-weight:bold">Scheduled Task</span> | Process matched an active Windows Task Scheduler task (`schtasks`). |
| <span style="color:#22d3ee font-weight:bold">Windows Service</span> | Process matched a registered Windows Service (`sc query`). |
| <span style="color:#94a3b8 font-weight:bold">Interactive / Shell</span> | Process was spawned by user action in Windows Explorer or terminal. |
| <span style="color:#f43f5e font-weight:bold">Unknown Origin</span> | **No known trigger source found!** Flagged for audit. |

---

## 6. Suspicious Command Detection Rules

SentinelLog includes a customizable security rules engine (`collector/rules.js`). It automatically tags events with a risk level and reason string:

| Risk Level | Trigger Pattern Example | Security Concern |
| :---: | :--- | :--- |
| 🚨 **HIGH** | `powershell -enc ...` / `-ec` | Base64-encoded PowerShell command (obfuscation). |
| 🚨 **HIGH** | `-NoProfile -WindowStyle Hidden` | Evasion flags hiding console window execution. |
| 🚨 **HIGH** | `IEX (New-Object Net.WebClient)` | Download-and-execute web cradle. |
| 🚨 **HIGH** | `certutil -urlcache -f ...` | LOLBin abuse for downloading external payloads. |
| 🚨 **HIGH** | `mshta`, `wscript` spawned by Office | Script execution initiated by Word/Excel/Browser. |
| ⚠️ **SUSPICIOUS** | `bitsadmin /transfer ...` | BITS transfer file download. |
| ⚠️ **SUSPICIOUS** | Unresolved origin + non-interactive | Background process popups with no trigger rule match. |
| ⚠️ **SUSPICIOUS** | Base64 string > 100 characters | Long entropy string in command line arguments. |

---

## 7. Running as a Permanent Windows Background Service

To keep SentinelLog capturing events continuously across system reboots:

1. Open **Command Prompt / PowerShell as Administrator**.
2. Run the service installer:
   ```cmd
   npm run install-service
   ```
3. SentinelLog Collector will now run as a background service named **"SentinelLog Collector"** (visible in `services.msc`).
4. To stop or uninstall the service:
   ```cmd
   npm run uninstall-service
   ```

---

## 8. Troubleshooting & FAQs

### Q: Why do I see "Channel not found: Sysmon" in collector logs?
- **Answer**: Sysmon is not installed yet. Run `.\setup\install-sysmon.ps1` from an elevated PowerShell prompt after placing `Sysmon64.exe` in `sentinellog/tools/`.

### Q: Does SentinelLog log keystrokes typed inside `cmd.exe`?
- **Answer**: No. As documented, `cmd.exe` has no built-in transcription. SentinelLog logs all `cmd.exe` process invocations and parameters (e.g. `cmd /c whoami`), but does not perform keylogging inside open interactive prompts.

### Q: Does SentinelLog make any external network requests?
- **Answer**: No. SentinelLog is 100% offline. All libraries (Tailwind v4, Recharts, Lucide, fonts) are bundled locally. Express binds to `127.0.0.1` only.

---

*SentinelLog Operational Manual — Local Windows Security Monitoring*
