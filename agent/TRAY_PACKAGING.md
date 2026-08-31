# Bhudi Tray build and startup integration

## Packaging

Package the tray companion as `BhudiTray.exe` using PyInstaller:

```powershell
pyinstaller --noconsole --onefile --name BhudiTray agent/bhudi_tray.py
```

## Startup

The installer should create a per-user startup entry for BhudiTray.exe. The background Bhudi agent remains a Windows service; the tray application runs in the interactive user session.

## Required installer payload

- BhudiTray.exe
- ProgramData\\Bhudi\\tray.json (agent identity/API configuration)

Do not embed long-lived tenant secrets in the executable. Credentials must be provisioned through the enrolled agent configuration and rotated/revoked server-side.
