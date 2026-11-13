# Phases 18–20 — Notifications, AI, Production Infrastructure

## Phase 18 — Notification Engine

Channels: **email, sms, teams, slack, discord, whatsapp, push, webhook**

```
GET  /api/v1/notifications/catalog
POST /api/v1/notifications/channels
POST /api/v1/notifications/templates
POST /api/v1/notifications/send
GET  /api/v1/notifications/deliveries
```

Missing provider config → `dry_run` delivery (safe for labs).

## Phase 19 — AI

```
POST /api/v1/ai/chat
POST /api/v1/ai/root-cause
POST /api/v1/ai/script
POST /api/v1/ai/remediation
POST /api/v1/ai/ticket-summary
POST /api/v1/ai/knowledge/search
POST /api/v1/ai/predictive-failure
POST /api/v1/ai/capacity-forecast
GET  /api/v1/ai/runs
```

**Full deploy guide:** [docs/AI_DEPLOYMENT.md](../docs/AI_DEPLOYMENT.md)

| Variable | Purpose |
|----------|---------|
| `AI_ENABLED` | `true` to allow live LLM calls |
| `AI_API_KEY` | OpenAI-compatible API key |
| `AI_BASE_URL` | Default `https://api.openai.com/v1` |
| `AI_MODEL` | Default `gpt-4o-mini` |

Without keys, endpoints and the side panel use **Guided mode** (heuristic / dry-run).

**Railway:** set the four variables on the **API** service → restart → UI shows **Live model**.

**Docker Compose:** put the same keys in `.env`; they are passed into the `api` service.

## Phase 20 — Production stack

```bash
docker compose up -d
alembic upgrade head   # inside API container or host
./scripts/backup_postgres.sh ./backups
```

| Component | Role |
|-----------|------|
| Docker Compose | API, Postgres, Redis, RabbitMQ, Nginx, Prometheus, Grafana, OTel |
| Kubernetes | `deploy/k8s/api-deployment.yaml` + HPA |
| Railway | `railway.toml` / `railway.json` → `backend/Dockerfile` |
| Nginx | TLS edge / rate limit zone |
| Redis / RabbitMQ | cache & async bus (URLs via env) |
| Prometheus / Grafana | metrics + dashboards |
| OpenTelemetry | OTLP :4317/:4318 |
| CI/CD | `.github/workflows/ci.yml` → GHCR |
| Rate limiting | `RateLimitMiddleware` (`RATE_LIMIT_PER_MINUTE`) |
| Backups | `scripts/backup_postgres.sh` |

Apply DB migrations through **PSA** (`f2a3b4c5d6e7`) and **notifications/AI** (`a3b4c5d6e7f8`).
