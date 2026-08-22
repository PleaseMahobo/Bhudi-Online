# Alert-driven remediation (production)

## Overview

When an `AlertRule` fires via `MonitoringService.raise_alert`, Bhudi can queue **remediation actions** on the matched device.

## Schema

### `AlertRule.remediation_actions` (JSON list)

```json
[
  {
    "name": "Restart print spooler",
    "type": "run_script",
    "enabled": true,
    "shell": "powershell",
    "script_content": "Restart-Service -Name Spooler -Force",
    "min_severity": "warning",
    "cooldown_seconds": 900,
    "dry_run": false,
    "ignore_suppression": false
  }
]
```

**Types:** `run_script` | `run_command` | `inventory_refresh` | `notify_only`

### `RemediationRun` audit table

Tracks every attempt: `queued` | `skipped` | `dry_run` | `failed` | `completed` with `skip_reason` (`cooldown_active`, `severity_gate`, `device_unresolved`, `alert_suppressed`, …).

## Runtime safety

| Guard | Behavior |
|-------|----------|
| Isolation | Failures never break alert persistence |
| Cooldown | Per fingerprint + action name (default 15m) |
| Severity gate | Only run if alert severity ≥ `min_severity` |
| Suppression | Skipped unless `ignore_suppression` |
| Dry run | Records intent without `ScriptTask` |
| Max actions | 5 per alert |

## Hook

`MonitoringService.raise_alert` → `_trigger_remediation` → `RemediationService.process_alert`.

Device resolution: `context.device_id` → check `target` as device id/hostname.

## API

- Rule CRUD already under `/api/v1/alert-engine/rules` (now accepts `remediation_actions`)
- `GET /api/v1/alert-engine/remediation-runs`

## UI

Alert Engine → edit rule → **Remediation actions** editor + recent runs panel.

## DB note

Ensure `alert_rules.remediation_actions` (JSON) and `remediation_runs` table exist (SQLAlchemy create_all or migration).
