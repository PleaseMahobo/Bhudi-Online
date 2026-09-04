# Bhudi production agent (Tactical-aligned)

## Architecture

Aligned with Tactical RMM’s practical split:

1. **Service agent** (`agent/native`) — always-on under LocalSystem  
   - Enroll / heartbeat / command poll  
   - Remote shell & desktop hooks  
   - **Windows Update patch scan & install**  
   - Live CPU / memory / disk metrics  

2. **User support client** (`agent/support-client`) — tray + tickets  
   - End-user ticket stub (ITSM via `/api/v1/agent-support/tickets`)  
   - Runs in the logged-on user session  

## Build matrix

```bash
# Agent
cd agent/native
CGO_ENABLED=0 go build -ldflags="-s -w -X main.agentVersion=2.2.0" -o bhudi-agent.exe .

# Tray client (Windows)
cd ../support-client
go build -ldflags="-s -w -H windowsgui" -o bhudi-support.exe .
```

Copy both into the same folder, then:

```bat
bhudi-agent.exe install -server https://your-api.example.com
```

## MSI

WiX package installs service + Support Client binary. See `agent/msi/Product.wxs`.

## Feature checklist vs Tactical RMM

| Capability | Status |
|------------|--------|
| Go Windows service agent | Yes |
| Heartbeat + pending commands | Yes |
| Live CPU / RAM / disk metrics | Yes (`gopsutil`) |
| Remote command / script | Yes |
| Remote terminal / desktop hooks | Partial (native modules present; portal polish remaining) |
| End-user tray ticket UI | Yes (support-client) |
| ITSM ticket API from agent | Yes (`agent_support`) |
| **Patch scan (Windows Update)** | **Yes** (`patch_scan` → COM via PowerShell) |
| **Patch install (Windows Update)** | **Yes** (`patch_install`; optional KB filter) |
| Patch rings / rollouts (portal) | Backend yes; queue agent commands on execute |
| MeshCentral dependency | Not required (Bhudi native path) |

## Patch commands

Queue from portal / API as enterprise or runtime commands:

| `command_type` | Behaviour |
|----------------|-----------|
| `patch_scan` | Lists missing Windows software updates (JSON in stdout) |
| `patch_install` | Downloads + installs missing updates; payload may include `kb` / `update_id` / `max_updates` |

Requires the agent service running as **LocalSystem** (or admin) so Windows Update COM works.

## Ops notes

- Identity: `%ProgramData%\Bhudi\Agent\agent_identity.json`
- Config: `agent_config.json` (`server_url`)
- Install log: `install.log` under the same data dir
