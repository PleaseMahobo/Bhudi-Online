# Bhudi observability (Prometheus + Alertmanager + Loki + Grafana)

## Stack ports

| Service | URL |
|---------|-----|
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Loki | http://localhost:3100 |

```bash
cd deploy/grafana
export GRAFANA_ADMIN_PASSWORD='strong-password'
docker compose up -d
```

---

## Prometheus recording rules

File: `deploy/prometheus/rules/recording.yml`

Pre-aggregated series (faster dashboards/alerts):

| Recording metric | Meaning |
|------------------|---------|
| `job:bhudi_http_requests:rate5m` | Request rate |
| `job:bhudi_http_error_rate:ratio5m` | 5xx ratio |
| `job:bhudi_http_request_duration:p50/p95/p99` | Latency quantiles |
| `job:bhudi_heartbeats:rate5m` | Heartbeat rate |
| `job:bhudi_agents_online:max` | Online agents |
| `job:bhudi_device_cpu:avg` | Fleet avg CPU |

Verify in Prometheus → **Graph**:

```promql
job:bhudi_http_error_rate:ratio5m
job:bhudi_http_request_duration:p95
```

Reload after edits:

```bash
curl -X POST http://localhost:9090/-/reload
```

---

## Alerting rules

File: `deploy/prometheus/rules/alerts.yml`

| Alert | Condition |
|-------|-----------|
| `BhudiAPIDown` | scrape `up == 0` for 2m |
| `BhudiAPIHighErrorRate` | 5xx ratio >5% for 5m |
| `BhudiAPIHighLatencyP95` | p95 >2s for 5m |
| `BhudiAPIHighLatencyP99` | p99 >5s for 5m |
| `BhudiNoAgentsOnline` | agents == 0 for 15m |
| `BhudiHeartbeatSilence` | online but no heartbeats 10m |
| `BhudiDeviceHighCPU` | CPU >90% for 10m |
| `BhudiDeviceHighMemory` | mem >90% for 10m |
| `BhudiAuthFailureSpike` | auth fail rate elevated |

Check **Prometheus → Alerts** and **Alertmanager** UI.

### Wire Slack / email

Edit `deploy/prometheus/alertmanager.yml`:

```yaml
receivers:
  - name: critical
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX'
        channel: '#bhudi-alerts'
        send_resolved: true
```

Restart Alertmanager:

```bash
docker compose restart alertmanager
```

---

## Grafana Loki (logs)

### How logs flow

```
Containers / files → Promtail → Loki → Grafana Explore (Loki)
```

Promtail tails Docker logs via `/var/run/docker.sock` and optional `/var/log/bhudi/*.log`.

### Explore logs

Grafana → **Explore** → datasource **Loki**:

```logql
{container=~".*api.*"} |= "ERROR"
{job="bhudi-api"} |~ "(?i)exception|traceback"
{service="grafana"}
```

Dashboard: **Bhudi Logs & Alerts** (`logs-and-alerts.json`).

### Railway / production logs

Railway already stores deploy logs. Options:

1. **Grafana Cloud Loki** free tier + ship with their agent, or  
2. App → HTTP push to Loki (`/loki/api/v1/push`) from a logging handler, or  
3. Keep Promtail only on hosts where Docker logs are available.

---

## Datasource checklist

1. **Prometheus** → `http://prometheus:9090` → Save & test  
2. **Loki** → `http://loki:3100` → Save & test  
3. **Bhudi Postgres** (optional history) → Supabase host, SSL require  
4. Confirm production scrape: Prometheus → Status → Targets → `bhudi-api-production` UP  

API metrics endpoint:

```bash
curl -sS https://bhudi-online-production.up.railway.app/metrics | head
```

---

## Files map

```
deploy/prometheus/prometheus.yml
deploy/prometheus/rules/recording.yml
deploy/prometheus/rules/alerts.yml
deploy/prometheus/alertmanager.yml
deploy/loki/loki-config.yml
deploy/loki/promtail-config.yml
deploy/grafana/docker-compose.yml
deploy/grafana/provisioning/datasources/datasources.yml
deploy/grafana/dashboards/*.json
```
