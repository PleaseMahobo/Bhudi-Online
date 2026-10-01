# Deploy Bhudi API to Railway (#64 wizard / invite)

Production: `https://bhudi-online-production.up.railway.app`

Code for customer wizard + invite is on **GitHub `main`**. The live process only updates after Railway rebuilds.

## Fastest path (dashboard — do this now)

1. Open [railway.app](https://railway.app) → project **bhudi-online-production** (or your API project).
2. Select the **API** service.
3. **Settings → Source**
   - Connect GitHub: `PleaseMahobo/Bhudi-Online`, branch **`main`**.
   - Root / Dockerfile: `backend` + `Dockerfile`, or use repo-root `railway.toml`.
4. Click **Deploy** / **Redeploy**.
5. Wait until the deployment is **Success**.
6. Verify (expect **401/403/422**, not **404**):

```bash
curl -sS -X POST https://bhudi-online-production.up.railway.app/api/v1/msp/customers/wizard \
  -H 'Content-Type: application/json' -d '{}'

curl -sS -X POST https://bhudi-online-production.up.railway.app/api/v1/msp/users/invite \
  -H 'Content-Type: application/json' -d '{}'
```

## Automate via GitHub Actions

Workflow: `.github/workflows/deploy-railway.yml`

Runs on `main` pushes that touch `backend/**`, or manually (**Actions → Deploy API (Railway) → Run workflow**).

### Secrets (repo → Settings → Secrets and variables → Actions)

| Secret | Required | How to get |
|--------|----------|------------|
| `RAILWAY_TOKEN` | **Yes** | Railway → Project → Settings → **Tokens** → Project Token |
| `RAILWAY_SERVICE_ID` | Recommended | Service → Settings → copy service id |
| `RAILWAY_ENVIRONMENT` | Optional | e.g. `production` |

After the secret exists, trigger **workflow_dispatch** once to ship current `main` (includes #64) without waiting for another backend commit.

## Why the UI alone is not enough

Vercel hosts the Next.js UI. Wizard/invite buttons call:

- `POST /api/v1/msp/customers/wizard`
- `POST /api/v1/msp/users/invite`

Those routes live in the **FastAPI** container on Railway. Until that container is redeployed from current `main`, the API returns **404**.
