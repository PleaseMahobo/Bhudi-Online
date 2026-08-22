# Alert-driven remediation (production)

When an `AlertRule` fires via `MonitoringService.raise_alert`, Bhudi can queue remediation actions on the matched device.

## Schema

`AlertRule.remediation_actions` — JSON list of actions (`run_script`, `run_command`, `inventory_refresh`, `notify_only`).

`RemediationRun` — audit table for every attempt.

## Safety

- Failures never break alert persistence
- Cooldown per fingerprint + action (default 15m)
- Severity gate, suppression respect, dry-run, max 5 actions

## API

- Rule CRUD accepts `remediation_actions`
- `GET /api/v1/alert-engine/remediation-runs`

## Deploy

Migrate `alert_rules.remediation_actions` and `remediation_runs`. Start with `dry_run: true`.
