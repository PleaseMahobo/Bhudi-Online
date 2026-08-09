# Bhudi Agent

Python RMM agent that enrolls with the Bhudi backend, heartbeats metrics, and executes commands / software deployments.

## Quick install

### Windows (recommended)

**Option A — one-liner** (from an elevated PowerShell):

```powershell
irm "https://<your-frontend-host>/api/agent/download?os=windows&server=<backend-url>" | iex
```

**Option B — download script**

1. Download `install.ps1` from the Bhudi console (**Install Agent** panel) or `/api/agent/download?os=windows`.
2. Right-click → **Run with PowerShell**, or:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install.ps1 -ServerUrl "https://bhudi-online-production.up.railway.app"
```

**Option C — double-click** `install.bat` (requests Administrator elevation).

### Linux / macOS

```bash
curl -fsSL "https://<your-frontend-host>/api/agent/download?os=linux&server=<backend-url>" | bash
```

Or:

```bash
chmod +x install.sh
./install.sh --server-url "https://bhudi-online-production.up.railway.app"
```

## What the installer does

1. Downloads the `agent/` package from the GitHub `main` branch
2. Installs into `Program Files\BhudiAgent` (Windows admin) or `%LOCALAPPDATA%\BhudiAgent` / `~/.local/share/bhudi-agent`
3. Creates a Python venv and installs `requirements.txt`
4. Writes `agent_config.json` with `server_url`
5. Registers a startup task (Windows Scheduled Task or systemd user unit)
6. Starts the agent (enrolls on first heartbeat)

## Manual run

```bash
export BHUDI_SERVER_URL=https://bhudi-online-production.up.railway.app
cd agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## MSI / EXE packaging (optional)

`installer.ini` is an [Inno Setup](https://jrsoftware.org/isinfo.php) script template that packages a PyInstaller `agent.exe`:

```bash
pip install pyinstaller
pyinstaller --onefile main.py -n agent
# Then compile installer.ini with Inno Setup → output/bhudi-agent-installer.exe
```

## Requirements

- Python 3.10+
- Network access to the Bhudi API (`/api/v1/runtime/...`)
- Windows: PowerShell 5.1+; Linux: `curl`, `unzip`, `python3`
