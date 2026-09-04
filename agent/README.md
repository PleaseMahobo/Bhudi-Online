# Bhudi Agent

**Production path: native static binary (Go).** No Python on endpoints.

Aligned with Tactical RMM-style architecture: **service agent** + **user-session support client** (system tray + tickets).

| Artifact | Use case |
|----------|----------|
| `BhudiAgent-Setup.exe` | Customer-specific Windows install (enrollment token embedded by portal) — **GUI wizard** |
| `bhudi-agent-setup.msi` | Intune / GPO / silent enterprise deploy |
| `bhudi-agent.exe` | Manual Windows binary (`install` / `upgrade` / `uninstall`) |
| `bhudi-support.exe` | System tray + end-user ticket UI (ship next to agent) |
| `bhudi-agent-linux-*` | Linux servers & workstations |
| `bhudi-agent-darwin-*` | macOS |

Release tag: [`agent-native-latest`](https://github.com/PleaseMahobo/Bhudi-Online/releases/tag/agent-native-latest)

See **[PRODUCTION_AGENT.md](./PRODUCTION_AGENT.md)** for the full production checklist.

## Recommended: GUI Installer (Windows)

Download the customer-specific `BhudiAgent-Setup.exe` from the Bhudi portal.

- Graphical wizard (no shell window)
- Installs **both** the Agent service and the Support Client in one run
- Uses the embedded enrollment token and server URL

Default production API: `https://bhudi-online-production.up.railway.app`

## Enterprise Windows (MSI)

```bat
msiexec /i bhudi-agent-setup.msi /qn SERVERURL=https://bhudi-online-production.up.railway.app
```

## Manual native install

Build agent + support client, place both in the same folder:

```bat
bhudi-agent.exe install -server https://bhudi-online-production.up.railway.app
bhudi-agent.exe upgrade -server https://bhudi-online-production.up.railway.app
bhudi-agent.exe uninstall
```

Install registers:

- Windows service `BhudiAgent` (LocalSystem)
- Watchdog scheduled task
- Support client logon task `BhudiSupport` (when `bhudi-support.exe` is present)
