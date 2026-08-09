# Bhudi Native Agent

**Standalone static binary. No Python on the endpoint.**

Works on ordinary Windows, Linux, and macOS machines used by end users — the same model as commercial RMM agents.

## Downloads (CI release `agent-native-latest`)

| File | Platform |
|------|----------|
| `bhudi-agent.exe` | Windows x64 |
| `bhudi-agent-setup.msi` | Windows MSI (Intune / GPO) |
| `bhudi-agent-linux-amd64` | Linux x64 |
| `bhudi-agent-linux-arm64` | Linux ARM64 |
| `bhudi-agent-darwin-amd64` | macOS Intel |
| `bhudi-agent-darwin-arm64` | macOS Apple Silicon |

Release: https://github.com/PleaseMahobo/Bhudi-Online/releases/tag/agent-native-latest

## Install

### Windows
```bat
bhudi-agent.exe install -server https://your-backend.example.com
```
Or deploy `bhudi-agent-setup.msi` (runs install automatically).

### Linux
```bash
chmod +x bhudi-agent-linux-amd64
sudo ./bhudi-agent-linux-amd64 install -server https://your-backend.example.com
```

### macOS
```bash
chmod +x bhudi-agent-darwin-arm64
./bhudi-agent-darwin-arm64 install -server https://your-backend.example.com
```

## What it does

1. Enrolls with `POST /api/v1/runtime/enroll`
2. Heartbeats on an interval
3. Polls and runs shell commands
4. Persists identity under OS-appropriate data dirs
5. Installs as Scheduled Task (Windows), systemd user unit (Linux), or LaunchAgent (macOS)

## Build

```bash
cd agent/native
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -ldflags="-s -w" -o bhudi-agent.exe .
```
