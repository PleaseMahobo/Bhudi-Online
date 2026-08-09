# Bhudi Agent MSI

Windows Installer package built with [WiX Toolset](https://wixtoolset.org/) v4/v5.

## What the MSI does

1. Installs `bhudi-agent-setup.exe` into `Program Files\Bhudi Agent`
2. Registers Add/Remove Programs entry
3. Runs the setup EXE once after install (downloads agent code, venv, scheduled task)
4. Optional property `SERVERURL` sets the Bhudi backend URL

## Install

```bat
msiexec /i bhudi-agent-setup.msi /qb
```

With custom server:

```bat
msiexec /i bhudi-agent-setup.msi SERVERURL=https://your-backend.example.com /qb
```

Silent:

```bat
msiexec /i bhudi-agent-setup.msi /qn
```

Uninstall:

```bat
msiexec /x bhudi-agent-setup.msi /qb
```

## Build locally (Windows)

1. Install [WiX v5](https://wixtoolset.org/) (`dotnet tool install -g wix` and `wix extension add WixToolset.UI.wixext`)
2. Build the setup EXE first:

```bat
cd ..\cmd\bhudi-agent-setup
set GOOS=windows
set GOARCH=amd64
go build -ldflags="-s -w" -o ..\..\msi\bhudi-agent-setup.exe .
```

3. Build the MSI:

```bat
cd ..\..\msi
wix extension add WixToolset.UI.wixext
wix build Product.wxs -ext WixToolset.UI.wixext -bindpath:setup=. -o bhudi-agent-setup.msi
```

## CI

`.github/workflows/build-agent-setup.yml` builds both the EXE and MSI and attaches them to the `agent-setup-latest` GitHub release.

## Intune / GPO

Deploy `bhudi-agent-setup.msi` as a Line-of-Business app. Ensure target devices have **Python 3.10+** on PATH (or pre-install via another package). For silent install use `/qn` and set `SERVERURL` if needed.
