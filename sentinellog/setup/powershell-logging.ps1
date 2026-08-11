# Check for Administrator privileges at runtime
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[WARNING] Administrator privileges are required to modify registry keys." -ForegroundColor Yellow
    Write-Host "          Please run PowerShell as Administrator to enable Script Block / Module Logging." -ForegroundColor Yellow
    Write-Host "          Command: Start-Process powershell -Verb RunAs -ArgumentList '-File .\setup\powershell-logging.ps1'" -ForegroundColor Gray
}

$ErrorActionPreference = "Continue"

$TranscriptDir = "C:\SentinelLog\transcripts"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SentinelLog — PowerShell Logging Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Enable Script Block Logging ─────────────────────────────────────
# This captures the full content of PowerShell scripts/commands as they execute.
# Events appear as Event ID 4104 in Microsoft-Windows-PowerShell/Operational.
Write-Host "[1/3] Enabling Script Block Logging..." -ForegroundColor Cyan

$sbPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging"
if (-not (Test-Path $sbPath)) {
    New-Item -Path $sbPath -Force | Out-Null
}
Set-ItemProperty -Path $sbPath -Name "EnableScriptBlockLogging" -Value 1 -Type DWord
Set-ItemProperty -Path $sbPath -Name "EnableScriptBlockInvocationLogging" -Value 1 -Type DWord

Write-Host "  [OK] ScriptBlockLogging = Enabled" -ForegroundColor Green
Write-Host "  [OK] ScriptBlockInvocationLogging = Enabled" -ForegroundColor Green
Write-Host "       Events: Event ID 4104 in Microsoft-Windows-PowerShell/Operational" -ForegroundColor Gray

# ── Step 2: Enable Module Logging ───────────────────────────────────────────
# This captures pipeline execution details for specified modules.
# Events appear as Event ID 4103 in Microsoft-Windows-PowerShell/Operational.
# Setting "*" logs ALL modules.
Write-Host ""
Write-Host "[2/3] Enabling Module Logging..." -ForegroundColor Cyan

$mlPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging"
if (-not (Test-Path $mlPath)) {
    New-Item -Path $mlPath -Force | Out-Null
}
Set-ItemProperty -Path $mlPath -Name "EnableModuleLogging" -Value 1 -Type DWord

# Log ALL modules by setting the module names to "*"
$mlNamesPath = "$mlPath\ModuleNames"
if (-not (Test-Path $mlNamesPath)) {
    New-Item -Path $mlNamesPath -Force | Out-Null
}
Set-ItemProperty -Path $mlNamesPath -Name "*" -Value "*" -Type String

Write-Host "  [OK] ModuleLogging = Enabled (all modules)" -ForegroundColor Green
Write-Host "       Events: Event ID 4103 in Microsoft-Windows-PowerShell/Operational" -ForegroundColor Gray

# ── Step 3: Enable Transcription ────────────────────────────────────────────
# This creates flat-file transcripts of all PowerShell sessions.
# Serves as a redundant secondary source alongside Event Log.
Write-Host ""
Write-Host "[3/3] Enabling Transcription..." -ForegroundColor Cyan

$trPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\Transcription"
if (-not (Test-Path $trPath)) {
    New-Item -Path $trPath -Force | Out-Null
}
Set-ItemProperty -Path $trPath -Name "EnableTranscripting" -Value 1 -Type DWord
Set-ItemProperty -Path $trPath -Name "EnableInvocationHeader" -Value 1 -Type DWord
Set-ItemProperty -Path $trPath -Name "OutputDirectory" -Value $TranscriptDir -Type String

# Create the transcript output directory if it doesn't exist
if (-not (Test-Path $TranscriptDir)) {
    New-Item -Path $TranscriptDir -ItemType Directory -Force | Out-Null
    Write-Host "  [OK] Created transcript directory: $TranscriptDir" -ForegroundColor Green
} else {
    Write-Host "  [OK] Transcript directory already exists: $TranscriptDir" -ForegroundColor Green
}

Write-Host "  [OK] Transcription = Enabled" -ForegroundColor Green
Write-Host "  [OK] InvocationHeader = Enabled" -ForegroundColor Green
Write-Host "       Output: $TranscriptDir" -ForegroundColor Gray

# ── Summary ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  All PowerShell logging enabled!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "What's now being captured:" -ForegroundColor Cyan
Write-Host "  - Script Block Logging (Event ID 4104): Full script/command content" -ForegroundColor White
Write-Host "  - Module Logging (Event ID 4103): Pipeline execution details" -ForegroundColor White
Write-Host "  - Transcription: Full session transcripts in $TranscriptDir" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Yellow
Write-Host "  - Changes apply to NEW PowerShell sessions only." -ForegroundColor Yellow
Write-Host "  - Existing open PowerShell windows are NOT affected." -ForegroundColor Yellow
Write-Host "  - Close and reopen PowerShell to start capturing." -ForegroundColor Yellow
Write-Host ""
Write-Host "To verify, open a new PowerShell window and run:" -ForegroundColor Gray
Write-Host "  Get-WinEvent -LogName 'Microsoft-Windows-PowerShell/Operational' -MaxEvents 5" -ForegroundColor Gray
