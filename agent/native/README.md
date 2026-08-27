# Bhudi Native Agent (enterprise)

Static Go agent — **no Python** on the endpoint.

## Commands

| Command | Purpose |
|---------|--------|
| `enroll -server URL` | Persist agent identity |
| `install -server URL` | Install OS service (elevated on Windows) |
| `upgrade -server URL` | Replace binary, restart service, **keep identity** |
| `uninstall` | Remove service / tasks / startup |
| `run -server URL` | Foreground (debug) |
| `version` | Print version |

## Enterprise Windows

1. **MSI (preferred for fleets)**  
   `msiexec /i bhudi-agent-setup.msi /qn SERVERURL=https://api.example.com`
2. **Customer EXE (portal)** — single-tenant enrollment token embedded.
3. **Manual** — `bhudi-agent.exe install -server ...` as Administrator.

Service: `BhudiAgent` (LocalSystem, delayed auto-start, restart on failure).

## Linux

- **Root:** system unit `/etc/systemd/system/bhudi-agent.service`
- **User:** `~/.config/systemd/user` + optional `loginctl enable-linger`

## Build

```bash
cd agent/native
CGO_ENABLED=0 go build -ldflags="-s -w -X main.agentVersion=2.1.0" -o bhudi-agent .
```
