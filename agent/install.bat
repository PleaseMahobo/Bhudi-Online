@echo off
REM Bhudi Agent Windows launcher — elevates and runs install.ps1
setlocal
set SCRIPT_DIR=%~dp0
set PS1=%SCRIPT_DIR%install.ps1

if not exist "%PS1%" (
  echo [Bhudi] install.ps1 not found next to install.bat
  exit /b 1
)

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [Bhudi] Requesting Administrator privileges...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
if errorlevel 1 (
  echo [Bhudi] Install failed.
  pause
  exit /b 1
)
echo.
echo [Bhudi] Done.
pause
