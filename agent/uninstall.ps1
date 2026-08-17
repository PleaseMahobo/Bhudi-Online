#Requires -Version 5.1
[CmdletBinding()]
param(
  [string]$InstallDir = $(Join-Path ${env:ProgramFiles} "BhudiAgent"),
  [switch]$RemoveData
)
$ErrorActionPreference = "Stop"
$ServiceName = "BhudiAgent"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw "Run as Administrator." }
$venvPython = Join-Path $InstallDir ".venv\Scripts\python.exe"
$serviceScript = Join-Path $InstallDir "windows_service.py"
if (Test-Path $serviceScript) {
  Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
  if (Test-Path $venvPython) { & $venvPython $serviceScript remove 2>$null }
}
Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
if ($RemoveData) { Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue }
Write-Host "BhudiAgent service removed." -ForegroundColor Green
if (-not $RemoveData) { Write-Host "Agent files/data retained at $InstallDir" }
