# Bhudi Support Client (production)

Native **Windows system-tray** app for end users on managed endpoints.

Mirrors the Tactical RMM pattern of splitting:

| Process | Context | Role |
|---------|---------|------|
| `bhudi-agent.exe` | LocalSystem service | Heartbeat, commands, remote, inventory |
| `bhudi-support.exe` | Interactive user session | Tray UI + ticket logging |

## Features

- System tray menu: **Open ticket**, **My tickets**, connection status, Exit
- Local loopback HTML UI (no external browser dependency for auth cookies)
- Session token binding (`X-Bhudi-Session`)
- Proxies ticket create/list to `POST/GET /api/v1/agent-support/tickets` with `X-Bhudi-Agent-Token`
- Waits up to 90s for agent enrollment files under `%ProgramData%\Bhudi\Agent\`
- Single-instance lock file

## Build

```bash
cd agent/support-client
go build -ldflags="-s -w -H windowsgui" -o bhudi-support.exe .
```

Place `bhudi-support.exe` next to `bhudi-agent.exe` before `install`, or ship via MSI.

## Install behaviour

`bhudi-agent.exe install` copies the support client (when present) and registers:

- Logon scheduled task `BhudiSupport`
- Optional HKCU Run key `BhudiSupport`

## Backend

Requires router include of `app.api.v1.endpoints.agent_support` (already registered in `backend/app/api/v1/router.py`).
