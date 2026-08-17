#Requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)] [ValidatePattern('^https://')] [string]$ServerUrl,
  [Parameter(Mandatory=$true)] [string]$EnrollmentToken,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ServerUrl = $ServerUrl.TrimEnd('/')
$BootstrapUrl = 'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest/bhudi-agent-setup.exe'

function Write-Step($msg) { Write-Host "[Bhudi] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[Bhudi] $msg" -ForegroundColor Green }

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw 'Run this installer from an elevated PowerShell window (Run as Administrator).'
}
if ([string]::IsNullOrWhiteSpace($EnrollmentToken)) { throw 'A customer enrollment token is required. Generate one from the Bhudi portal.' }

$temp = Join-Path $env:TEMP ('bhudi-bootstrap-' + [guid]::NewGuid().ToString('n'))
$bootstrap = Join-Path $temp 'bhudi-agent-setup.exe'
New-Item -ItemType Directory -Path $temp -Force | Out-Null

try {
  Write-Step "Server URL: $ServerUrl"
  Write-Step 'Python: not required'
  Write-Step 'Downloading standalone Bhudi Windows installer...'
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -Uri $BootstrapUrl -OutFile $bootstrap -UseBasicParsing

  Write-Step 'Launching native installer...'
  $args = @('-server', $ServerUrl, '-enrollment-token', $EnrollmentToken)
  if ($Force) { $args += '-force' }
  $p = Start-Process -FilePath $bootstrap -ArgumentList $args -Verb RunAs -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Native Bhudi installer exited with code $($p.ExitCode)." }
  Write-Ok 'Bhudi Agent installed using the native Windows package. No Python was installed or required.'
} finally {
  Remove-Item -Path $temp -Recurse -Force -ErrorAction SilentlyContinue
}
