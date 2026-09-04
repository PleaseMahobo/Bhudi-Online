# Bhudi production agent (Tactical-aligned)

## Architecture

Aligned with Tactical RMM’s practical split:

1. **Service agent** (`agent/native`) — always-on under LocalSystem  
   - Enroll / heartbeat / command poll  
   - Remote shell & desktop hooks  
   - Inventory & script execution path  

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

WiX package installs service + optional Support Client binary. See `agent/msi/Product.wxs`.

## Feature checklist vs Tactical RMM

| Capability | Status |
|------------|--------|
| Go Windows service agent | Yes |
| Heartbeat + pending commands | Yes |
| Remote command / script | Yes |
| Remote terminal / desktop hooks | Partial (native modules present) |
| End-user tray ticket UI | Yes (support-client) |
| ITSM ticket API from agent | Yes (`agent_support`) |
| Patch mgmt / Chocolatey policies | Backend modules; agent policy runner roadmap |
| MeshCentral dependency | Not required (Bhudi native path) |

## Ops notes

- Identity: `%ProgramData%\Bhudi\Agent\agent_identity.json`
- Config: `agent_config.json` (`server_url`)
- Install log: `install.log` under the same data dir
