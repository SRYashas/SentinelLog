# Check for Administrator privileges at runtime
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[WARNING] Administrator privileges are required to install Sysmon service." -ForegroundColor Yellow
    Write-Host "          Please run PowerShell as Administrator to install Sysmon." -ForegroundColor Yellow
    Write-Host "          Command: Start-Process powershell -Verb RunAs -ArgumentList '-File .\setup\install-sysmon.ps1'" -ForegroundColor Gray
}

$ErrorActionPreference = "Continue"

# Resolve paths relative to this script's location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsDir = Join-Path (Split-Path -Parent $ScriptDir) "tools"
$SysmonExe = Join-Path $ToolsDir "Sysmon64.exe"
$SysmonConfig = Join-Path $ScriptDir "sysmon-config.xml"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SentinelLog — Sysmon Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Verify Sysmon64.exe exists ──────────────────────────────────────
if (-not (Test-Path $SysmonExe)) {
    Write-Host "[ERROR] Sysmon64.exe not found at:" -ForegroundColor Red
    Write-Host "        $SysmonExe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please download Sysmon from Microsoft Sysinternals:" -ForegroundColor Yellow
    Write-Host "  https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Then place Sysmon64.exe in the tools/ folder:" -ForegroundColor Yellow
    Write-Host "  $ToolsDir" -ForegroundColor Gray
    Write-Host ""
    Write-Host "This is a one-time manual step (offline requirement)." -ForegroundColor Yellow
    exit 1
}

# ── Step 2: Verify config file exists ───────────────────────────────────────
if (-not (Test-Path $SysmonConfig)) {
    Write-Host "[ERROR] Sysmon config not found at:" -ForegroundColor Red
    Write-Host "        $SysmonConfig" -ForegroundColor Yellow
    exit 1
}

# ── Step 3: Check if Sysmon is already installed ────────────────────────────
$sysmonService = Get-Service -Name "Sysmon64" -ErrorAction SilentlyContinue
if ($null -eq $sysmonService) {
    $sysmonService = Get-Service -Name "Sysmon" -ErrorAction SilentlyContinue
}

if ($null -ne $sysmonService) {
    # Sysmon is already installed — update the configuration
    Write-Host "[INFO] Sysmon is already installed (Status: $($sysmonService.Status))" -ForegroundColor Green
    Write-Host "[INFO] Updating Sysmon configuration..." -ForegroundColor Cyan

    & $SysmonExe -c $SysmonConfig 2>&1 | Write-Host

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[SUCCESS] Sysmon configuration updated successfully." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[WARNING] Sysmon config update returned exit code $LASTEXITCODE." -ForegroundColor Yellow
        Write-Host "          Check the output above for details." -ForegroundColor Yellow
    }
} else {
    # Sysmon is not installed — install fresh
    Write-Host "[INFO] Sysmon is not installed. Installing now..." -ForegroundColor Cyan
    Write-Host "[INFO] Using config: $SysmonConfig" -ForegroundColor Gray

    & $SysmonExe -accepteula -i $SysmonConfig 2>&1 | Write-Host

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[SUCCESS] Sysmon installed and configured successfully." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[ERROR] Sysmon installation failed with exit code $LASTEXITCODE." -ForegroundColor Red
        Write-Host "        Make sure you are running as Administrator." -ForegroundColor Yellow
        exit 1
    }
}

# ── Step 4: Verify the service is running ───────────────────────────────────
Write-Host ""
$svc = Get-Service -Name "Sysmon64" -ErrorAction SilentlyContinue
if ($null -eq $svc) {
    $svc = Get-Service -Name "Sysmon" -ErrorAction SilentlyContinue
}

if ($null -ne $svc -and $svc.Status -eq "Running") {
    Write-Host "[VERIFIED] Sysmon service is running." -ForegroundColor Green
    Write-Host ""
    Write-Host "Process creation events (Event ID 1) are now being logged to:" -ForegroundColor Cyan
    Write-Host "  Event Viewer > Applications and Services Logs > Microsoft > Windows > Sysmon > Operational" -ForegroundColor Gray
} else {
    Write-Host "[WARNING] Sysmon service may not be running. Check services.msc" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
