# Deep Buddy — deploy guide

Deep Buddy is the **tactical-class RMM** product skin in the **Bhudi Online** monorepo.
It reuses the Bhudi frontend (Next.js on Vercel) and API (FastAPI on Railway).

## 1. Live client / site tree

API:

```http
GET /api/v1/deep-buddy/tree
GET /api/v1/deep-buddy/status
```

- Prefer **MSP** `organizations` + `sites` from Postgres.
- Agent rows come from the **runtime** enroll store (`/api/v1/runtime/agents`).
- Assignment fields: `organization_id`, `site_id` (via device assignment APIs).
- If no orgs exist yet, the API returns a **seed tree** and attaches unassigned agents.

Console UI: `/deep-buddy/console/clients`

## 2. Dedicated Deep Buddy domain (Vercel)

### Option A — path on existing project (default)

| Path | Content |
|------|---------|
| `https://<bhudi-host>/deep-buddy` | Marketing |
| `https://<bhudi-host>/deep-buddy/console` | RMM console |

### Option B — dedicated hostname

1. **Vercel → Project → Settings → Domains** — add e.g. `rmm.yourdomain.com`.
2. DNS CNAME → Vercel.
3. Optional host-based rewrites: see `frontend/vercel.deep-buddy.example.json`.
4. Set `NEXT_PUBLIC_API_URL` to the Railway API base URL.
5. Redeploy.

### Environment

| Variable | Where | Purpose |
|----------|--------|---------|
| `NEXT_PUBLIC_API_URL` | Vercel | Backend base URL |
| `FRONTEND_URL` | Railway | Links / Stripe redirects |
| `BHUDI_RUNTIME_STORE` | Railway | Persist agent tokens |

## 3. Tactical RMM install scripts → Deep Buddy ops

Scripts in [PleaseMahobo/TacticalRmm](https://github.com/PleaseMahobo/TacticalRmm)
(`install.sh`, `update.sh`, `backup.sh`, `restore.sh`, `troubleshoot_server.sh`) target a **classic Tactical** stack under `/rmm`. **Do not run them expecting Deep Buddy paths.**

| Tactical (scripts) | Deep Buddy / Bhudi |
|--------------------|--------------------|
| Single VM `install.sh` | Railway (API) + Vercel (UI) |
| MeshCentral remote | Bhudi native agent remote desktop / terminal |
| OS agents | `agent/native` + `/agents` downloads |
| Client / site hierarchy | MSP orgs/sites + `/api/v1/deep-buddy/tree` |
| `backup.sh` | Railway DB backups + `BHUDI_RUNTIME_STORE` |
| `update.sh` | Git push → Vercel/Railway redeploy |

### Self-host API baseline (adapted from Tactical)

- x86_64 or aarch64 Linux VM (not LXC)
- ≥ 4 GB RAM for API + Postgres
- Docker Compose: repo `docker-compose.yml`

### Agent install

```text
bhudi-agent.exe install -server https://<your-api>
```

Confirm under `/deep-buddy/console/agents`.

## Quick checklist

- [ ] Railway API healthy
- [ ] Vercel frontend deployed
- [ ] `NEXT_PUBLIC_API_URL` set
- [ ] Open `/deep-buddy` and `/deep-buddy/console`
- [ ] Enroll at least one agent
- [ ] (Optional) Create MSP organizations/sites for full DB tree
- [ ] (Optional) Custom domain + rewrites

## Product split

| Product | URL |
|---------|-----|
| Bhudi Online | `/` |
| Deep Buddy RMM | `/deep-buddy` |
