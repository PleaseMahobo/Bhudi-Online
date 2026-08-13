# Grafana for Bhudi device metrics

## 1. Ensure DB schema + indexes

In **Supabase SQL Editor**, run:

`backend/scripts/ensure_auth_and_metrics_schema.sql`

This adds missing `users` columns (fixes register 500) and indexes on `device_metrics`.

## 2. Start Grafana

```bash
cd deploy/grafana
export GRAFANA_ADMIN_PASSWORD='pick-a-strong-password'
docker compose up -d
```

Open http://localhost:3001 — login `admin` / your password.

## 3. Connect Postgres (Supabase)

Grafana → Connections → Data sources → PostgreSQL:

| Field | Value |
|-------|--------|
| Host | `db.<project>.supabase.co:5432` (or pooler host) |
| Database | `postgres` |
| User | `postgres` or service role user |
| Password | database password |
| TLS/SSL | require |

## 4. Dashboard

Import `dashboards/device-metrics.json` or use the provisioned **Bhudi Device Metrics** board.

SQL used:

```sql
SELECT recorded_at AS time, cpu_usage, ram_usage, disk_usage
FROM device_metrics
WHERE recorded_at BETWEEN $__timeFrom() AND $__timeTo()
ORDER BY recorded_at;
```

## 5. App charts vs Grafana

| Surface | Purpose |
|---------|---------|
| Bhudi Devices page (Recharts) | Operators in product UI |
| Grafana | Deep history, ops/NOC, alerting |

Both read the same `device_metrics` table filled by agent heartbeats.
