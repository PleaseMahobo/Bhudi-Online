#Requires -Version 5.1
<#
.SYNOPSIS
  Bhudi RMM Agent installer for Windows.

.DESCRIPTION
  Downloads the agent from GitHub (or uses a local source), installs to
  Program Files\BhudiAgent, creates a venv, writes config, and registers a
  Scheduled Task to run at startup.

.PARAMETER ServerUrl
  Backend base URL (no trailing slash). Example:
  https://bhudi-online-production.up.railway.app

.PARAMETER InstallDir
  Install directory. Default: $env:ProgramFiles\BhudiAgent

.PARAMETER SkipTask
  Do not create the Scheduled Task (manual run only).

.EXAMPLE
  irm https://your-app.vercel.app/api/agent/download?os=windows | iex

.EXAMPLE
  .\install.ps1 -ServerUrl "https://bhudi-online-production.up.railway.app"
#>
[CmdletBinding()]
param(
  [string]$ServerUrl = $env:BHUDI_SERVER_URL,
  [string]$InstallDir = $(Join-Path ${env:ProgramFiles} "BhudiAgent"),
  [string]$RepoZipUrl = "https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip",
  [switch]$SkipTask,
  [switch]$StartNow
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "[Bhudi] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[Bhudi] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[Bhudi] $msg" -ForegroundColor Yellow }

if (-not $ServerUrl -or $ServerUrl.Trim() -eq "") {
  $ServerUrl = "https://bhudi-online-production.up.railway.app"
}
$ServerUrl = $ServerUrl.TrimEnd("/")

# Prefer elevation for Program Files + Scheduled Task
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  Write-Warn "Not running as Administrator. Install will use user profile and a per-user startup task."
  $InstallDir = Join-Path $env:LOCALAPPDATA "BhudiAgent"
}

Write-Step "Server URL: $ServerUrl"
Write-Step "Install dir: $InstallDir"

# --- Python ---
$python = $null
foreach ($cand in @("py", "python", "python3")) {
  try {
    $v = & $cand -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $v) { $python = $v.Trim(); break }
  } catch {}
}
if (-not $python) {
  throw "Python 3 was not found. Install Python 3.11+ from https://www.python.org/downloads/ (check 'Add python.exe to PATH') and re-run."
}
Write-Ok "Python: $python"

# --- Fetch agent sources ---
$temp = Join-Path $env:TEMP ("bhudi-agent-" + [guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Path $temp -Force | Out-Null
$zipPath = Join-Path $temp "repo.zip"

Write-Step "Downloading agent package..."
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -Uri $RepoZipUrl -OutFile $zipPath -UseBasicParsing
} catch {
  throw "Failed to download agent package from $RepoZipUrl. $_"
}

Expand-Archive -Path $zipPath -DestinationPath $temp -Force
$agentSrc = Get-ChildItem -Path $temp -Directory | Where-Object { $_.Name -like "Bhudi-Online-*" } | ForEach-Object { Join-Path $_.FullName "agent" } | Select-Object -First 1
if (-not $agentSrc -or -not (Test-Path (Join-Path $agentSrc "main.py"))) {
  throw "Could not locate agent/main.py inside the downloaded archive."
}

# --- Install files ---
if (Test-Path $InstallDir) {
  Write-Step "Updating existing install at $InstallDir"
} else {
  New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Copy-Item -Path (Join-Path $agentSrc "*") -Destination $InstallDir -Recurse -Force

$config = @{
  server_url          = $ServerUrl
  heartbeat_interval  = 10
}
$config | ConvertTo-Json | Set-Content -Path (Join-Path $InstallDir "agent_config.json") -Encoding UTF8

# --- venv + deps ---
$venvDir = Join-Path $InstallDir ".venv"
Write-Step "Creating virtual environment..."
& $python -m venv $venvDir
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$req = Join-Path $InstallDir "requirements.txt"
Write-Step "Installing dependencies..."
& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPython -m pip install -r $req
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# Runner script used by the scheduled task
$runner = @"
@echo off
set BHUDI_SERVER_URL=$ServerUrl
cd /d "$InstallDir"
"$venvPython" main.py
"@
$runnerPath = Join-Path $InstallDir "run-agent.bat"
Set-Content -Path $runnerPath -Value $runner -Encoding ASCII

# --- Scheduled Task ---
if (-not $SkipTask) {
  $taskName = "BhudiAgent"
  Write-Step "Registering Scheduled Task '$taskName'..."
  try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  } catch {}

  $action = New-ScheduledTaskAction -Execute $runnerPath
  if ($isAdmin) {
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
  } else {
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
  }
  $trigger = New-ScheduledTaskTrigger -AtStartup
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $taskPrincipal -Settings $settings -Force | Out-Null
  Write-Ok "Scheduled Task registered (runs at startup)."

  if ($StartNow -or $true) {
    try {
      Start-ScheduledTask -TaskName $taskName
      Write-Ok "Agent task started."
    } catch {
      Write-Warn "Could not start task immediately: $_"
      Write-Step "Starting agent in background..."
      Start-Process -FilePath $runnerPath -WindowStyle Hidden
    }
  }
} else {
  Write-Warn "SkipTask set — start manually with: $runnerPath"
}

# Cleanup
Remove-Item -Path $temp -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Ok "Bhudi Agent installed successfully."
Write-Host "  Directory : $InstallDir"
Write-Host "  Server    : $ServerUrl"
Write-Host "  Runner    : $runnerPath"
Write-Host ""
Write-Host "The agent will enroll on first heartbeat and appear under Devices / Assets." -ForegroundColor Gray
