#Requires -Version 5.1
<#
.SYNOPSIS
  Bhudi RMM Agent Windows service installer.
.DESCRIPTION
  Installs the agent under Program Files, creates an isolated virtual
  environment, installs dependencies, registers BhudiAgent as a native
  Windows service through pywin32, configures automatic startup/recovery,
  and starts the service.
  ServerUrl is required deliberately so a new endpoint can never silently
  point at production.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidatePattern('^https://')]
  [string]$ServerUrl,
  [string]$InstallDir = $(Join-Path ${env:ProgramFiles} "BhudiAgent"),
  [string]$RepoZipUrl = "https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip",
  [switch]$Force
)
$ErrorActionPreference = "Stop"
$ServiceName = "BhudiAgent"
function Write-Step($msg) { Write-Host "[Bhudi] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[Bhudi] $msg" -ForegroundColor Green }

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw "Run this installer from an elevated PowerShell window (Run as Administrator)."
}
$ServerUrl = $ServerUrl.TrimEnd('/')
Write-Step "Server URL: $ServerUrl"
Write-Step "Install dir: $InstallDir"

$python = $null
foreach ($cand in @("py", "python", "python3")) {
  try {
    $v = & $cand -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $v) { $python = $v.Trim(); break }
  } catch {}
}
if (-not $python) { throw "Python 3.11+ was not found. Install Python and rerun the installer." }
Write-Ok "Python: $python"

$temp = Join-Path $env:TEMP ("bhudi-agent-" + [guid]::NewGuid().ToString("n"))
$zipPath = Join-Path $temp "repo.zip"
New-Item -ItemType Directory -Path $temp -Force | Out-Null
try {
  Write-Step "Downloading Bhudi agent package..."
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -Uri $RepoZipUrl -OutFile $zipPath -UseBasicParsing
  Expand-Archive -Path $zipPath -DestinationPath $temp -Force
  $root = Get-ChildItem -Path $temp -Directory | Where-Object { $_.Name -like "Bhudi-Online-*" } | Select-Object -First 1
  $agentSrc = if ($root) { Join-Path $root.FullName "agent" } else { $null }
  if (-not $agentSrc -or -not (Test-Path (Join-Path $agentSrc "bhudi_agent.py"))) {
    throw "Downloaded package does not contain agent/bhudi_agent.py."
  }

  if (Test-Path $InstallDir) {
    if (-not $Force) { throw "$InstallDir already exists. Use -Force to replace it." }
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    if (Test-Path (Join-Path $InstallDir "windows_service.py")) {
      & $python (Join-Path $InstallDir "windows_service.py") remove 2>$null
    }
  }
  New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
  Copy-Item -Path (Join-Path $agentSrc "*") -Destination $InstallDir -Recurse -Force

  @{ server_url = $ServerUrl; heartbeat_interval = 30 } | ConvertTo-Json | Set-Content -Path (Join-Path $InstallDir "agent_config.json") -Encoding UTF8
  $venvDir = Join-Path $InstallDir ".venv"
  Write-Step "Creating isolated Python environment..."
  & $python -m venv $venvDir
  if ($LASTEXITCODE -ne 0) { throw "Python virtual environment creation failed." }
  $venvPython = Join-Path $venvDir "Scripts\python.exe"

  Write-Step "Installing agent dependencies..."
  # Pin pip below 26.0. The current pip 26.x packaging stack can reject
  # legacy metadata such as 0.dev0 on Windows/Python 3.12 environments.
  & $venvPython -m pip install --disable-pip-version-check "pip<26"
  if ($LASTEXITCODE -ne 0) { throw "pip bootstrap failed." }
  & $venvPython -m pip install --disable-pip-version-check -r (Join-Path $InstallDir "requirements.txt")
  if ($LASTEXITCODE -ne 0) { throw "Agent dependency installation failed." }

  Write-Step "Installing BhudiAgent Windows service..."
  & $venvPython (Join-Path $InstallDir "windows_service.py") install
  if ($LASTEXITCODE -ne 0) { throw "Windows service registration failed." }
  & $venvPython (Join-Path $InstallDir "windows_service.py") --startup auto update
  & sc.exe description $ServiceName "Bhudi remote monitoring, management and security agent." | Out-Null
  & sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

  Write-Step "Starting BhudiAgent..."
  & $venvPython (Join-Path $InstallDir "windows_service.py") start
  if ($LASTEXITCODE -ne 0) { throw "BhudiAgent service failed to start." }
  Start-Sleep -Seconds 3
  $svc = Get-Service -Name $ServiceName -ErrorAction Stop
  if ($svc.Status -ne "Running") { throw "BhudiAgent is not running. Inspect $InstallDir\agent-service.log." }

  Write-Ok "Bhudi Agent installed and running as a Windows service."
  Write-Host "  Service : $ServiceName"
  Write-Host "  Server  : $ServerUrl"
  Write-Host "  Install : $InstallDir"
} finally {
  Remove-Item -Path $temp -Recurse -Force -ErrorAction SilentlyContinue
}
