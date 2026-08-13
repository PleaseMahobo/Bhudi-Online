# Grafana + Prometheus for Bhudi

## Architecture

```
Agents --heartbeat--> Bhudi API --writes--> Postgres device_metrics
                         |
                         +--exposes--> GET /metrics  <--scrape-- Prometheus <-- Grafana
                         |
                         +--Grafana Postgres datasource--> historical graphs
```

| Source | Best for |
|--------|----------|
| **Prometheus** | Live rates, latency, online agents, last CPU/RAM gauges |
| **Postgres** | Long-range history, bucketed averages, fleet rollups |

---

## 1. API: Prometheus endpoint

After deploying the backend, verify:

```bash
curl -sS https://bhudi-online-production.up.railway.app/metrics | head
```

You should see series such as:

- `bhudi_http_requests_total`
- `bhudi_http_request_duration_seconds_bucket`
- `bhudi_agent_heartbeats_total`
- `bhudi_device_cpu_percent`
- `bhudi_agents_online`

---

## 2. Start stack

```bash
cd deploy/grafana
export GRAFANA_ADMIN_PASSWORD='use-a-strong-password'
# Optional Postgres for historical panels:
export BHUDI_PG_HOST='db.YOUR_PROJECT.supabase.co:5432'
export BHUDI_PG_USER='postgres'
export BHUDI_PG_PASSWORD='YOUR_DB_PASSWORD'
export BHUDI_PG_DATABASE='postgres'
export BHUDI_PG_SSLMODE='require'
docker compose up -d
```

- Grafana: http://localhost:3001 (admin / password above)
- Prometheus: http://localhost:9090

---

## 3. Grafana datasource configuration (UI steps)

### A. Prometheus (usually auto-provisioned)

1. Grafana → **Connections** → **Data sources**
2. Open **Prometheus** (or Add → Prometheus)
3. Settings:

| Field | Value |
|-------|--------|
| Name | `Prometheus` |
| URL | `http://prometheus:9090` (inside Compose) or `http://localhost:9090` |
| Scrape interval | `15s` |

4. **Save & test** → green “Data source is working”.

### B. Postgres / Supabase (historical `device_metrics`)

1. **Connections** → **Add data source** → **PostgreSQL**
2. Settings:

| Field | Value |
|-------|--------|
| Name | `Bhudi Postgres` |
| Host | `db.<project-ref>.supabase.co:5432` |
| Database | `postgres` |
| User | `postgres` (or pooler user) |
| Password | Database password from Supabase |
| TLS/SSL Mode | `require` |
| Version | 15+ |

3. **Save & test**.

**Supabase tips**

- Prefer **direct** connection for Grafana (not transaction pooler) if prepared statements fail.
- Session mode pooler port is often `6543`; direct is `5432`.
- Allow your Grafana host IP in Supabase network restrictions if enabled.

### C. Production API scrape

Edit `deploy/prometheus/prometheus.yml` job `bhudi-api-production` so `targets` match your Railway host, then:

```bash
curl -X POST http://localhost:9090/-/reload
```

Or restart: `docker compose restart prometheus`.

Confirm in Prometheus → **Status → Targets** that `bhudi-api-production` is **UP**.

---

## 4. Optimized dashboard queries

**Prometheus (live)**

```promql
sum(rate(bhudi_http_requests_total[5m]))
histogram_quantile(0.95, sum(rate(bhudi_http_request_duration_seconds_bucket[5m])) by (le))
bhudi_agents_online
bhudi_device_cpu_percent
```

**Postgres (bucketed history — avoids scanning every raw point)**

```sql
SELECT
  date_trunc('minute', recorded_at) AS time,
  ROUND(AVG(cpu_usage)::numeric, 2) AS avg_cpu,
  ROUND(AVG(ram_usage)::numeric, 2) AS avg_mem
FROM device_metrics
WHERE $__timeFilter(recorded_at)
  AND (COALESCE(TRIM('$device_id'), '') = '' OR device_id::text = TRIM('$device_id'))
GROUP BY 1
ORDER BY 1;
```

Indexes (already in `backend/scripts/ensure_auth_and_metrics_schema.sql`):

- `(device_id, recorded_at DESC)`
- `BRIN (recorded_at)`

---

## 5. App UI vs Grafana

| Surface | Role |
|---------|------|
| Bhudi **Devices** page (Recharts) | Operators inside the product |
| **Grafana** | NOC, SLA, deep history, PromQL alerting |

Both ultimately depend on agents sending heartbeats with CPU/RAM/disk.
