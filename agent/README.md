# Bhudi Agent

**Production path: native static binary (Go).** No Python on endpoints.

| Artifact | Use case |
|----------|----------|
| `BhudiAgent-Setup.exe` | Customer-specific Windows install (enrollment token embedded by portal) |
| `bhudi-agent-setup.msi` | Intune / GPO / silent enterprise deploy |
| `bhudi-agent.exe` | Manual Windows binary (`install` / `upgrade` / `uninstall`) |
| `bhudi-agent-linux-*` | Linux servers & workstations |
| `bhudi-agent-darwin-*` | macOS |

Release tag: [`agent-native-latest`](https://github.com/PleaseMahobo/Bhudi-Online/releases/tag/agent-native-latest)

## Enterprise Windows (MSI)

```bat
msiexec /i bhudi-agent-setup.msi /qn SERVERURL=https://your-api.example.com
```

## Manual native install

```bat
bhudi-agent.exe install -server https://your-api.example.com
bhudi-agent.exe upgrade -server https://your-api.example.com
bhudi-agent.exe uninstall
```

## Deprecated

`install.ps1` / `install.sh` (Python venv from GitHub zip) are **lab-only**. Do not use for production endpoints.
