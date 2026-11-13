# Command payload schemas (OpenAPI-style)

Enterprise commands use:

```http
POST /api/v1/commands
Content-Type: application/json

{
  "agent_id": "<uuid>",
  "command_type": "<string>",
  "payload": { },
  "priority": 50,
  "timeout_seconds": 300,
  "requires_reboot": false
}
```

Canonical field definitions live in `backend/app/commands/catalog.py` under each entry's `payload_schema`.
Agents poll `GET /api/v1/agent/{agent_id}/commands` and execute via `agent/command_framework.py`.

## Envelope

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `agent_id` | uuid | yes | Target agent |
| `command_type` | string | yes | Catalog `type` |
| `payload` | object | no | Defaults to `{}` |
| `priority` | integer | no | Default 5–50; high-risk actions often 90 |
| `timeout_seconds` | integer | no | 5–7200 |
| `requires_reboot` | boolean | no | Default false |

## Per `command_type` payloads

### Empty payload (`{}`)

`inventory`, `processes`, `services`, `software`, `windows_updates`, `network`, `disks`, `printers`, `endpoint_security`

### `event_logs`

```json
{
  "log_name": "Application",
  "limit": 100
}
```

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `log_name` | string | `Application` | `Application` \| `System` \| `Security` |
| `limit` | integer | `100` | 1–500 |

### `remote_script`

```json
{
  "script": "Write-Output 'hello'",
  "interpreter": "powershell",
  "timeout_seconds": 300,
  "working_directory": null
}
```

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `script` | string | **yes** | — | Full script body |
| `interpreter` | string | no | `powershell` | `powershell`, `pwsh`, `bash`, `sh`, `python` |
| `timeout_seconds` | integer | no | `300` | 5–7200 |
| `working_directory` | string | no | — | Optional cwd |

### `remote_powershell`

```json
{
  "command": "Get-Service | Where-Object Status -eq Running",
  "timeout_seconds": 300,
  "arguments": []
}
```

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `command` | string | **yes** | — | PowerShell command text |
| `timeout_seconds` | integer | no | `300` | 5–7200 |
| `arguments` | array | no | — | Extra CLI args |

## Related (not in Automation catalog)

### Patch rollout

```json
{
  "command_type": "patch_scan" | "patch_install",
  "payload": {
    "rollout_id": "<uuid>",
    "rollout_name": "..."
  }
}
```

### Remote access

`command_type` uses dotted names (`remote.desktop.start`, …). Payload always includes `operation` plus operation-specific fields (see `RemoteAccessService.list_capabilities()`).

## Result shape (agent → server)

```json
{
  "exit_code": 0,
  "stdout": "...",
  "stderr": "...",
  "metadata": { }
}
```

Collection commands typically serialize structured data as JSON in `stdout`.
