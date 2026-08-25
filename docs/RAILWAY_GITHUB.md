# Railway + GitHub integration (Bhudi API)

Production API: `https://bhudi-online-production.up.railway.app`

Repo CI (`.github/workflows/ci.yml`) builds and pushes
`ghcr.io/pleasemahobo/bhudi-online-api` on every `main` push.
**It does not deploy Railway.** Live updates require Railway to watch GitHub or GHCR.

## Recommended: GitHub source (auto-deploy on merge)

1. Open [Railway](https://railway.app) → project that hosts **bhudi-online-production**.
2. Select the **API** service.
3. **Settings → Source**
   - Connect **GitHub** if prompted (grant access to `PleaseMahobo/Bhudi-Online`).
   - Repository: `PleaseMahobo/Bhudi-Online`
   - Branch: `main`
   - Enable **Wait for CI** only if you want deploys after CI succeeds (optional).
4. **Settings → Build**
   - Builder: **Dockerfile** (repo root `railway.toml` points at `backend/Dockerfile`), **or**
   - Root Directory: `backend` and Dockerfile: `Dockerfile`.
5. **Settings → Deploy**
   - Healthcheck path: `/api/v1/health`
6. **Variables** (keep existing; do not wipe):
   - `DATABASE_URL`
   - `JWT_SECRET_KEY`
   - Supabase / Stripe / AI keys as already set
7. **Deploy → Redeploy** once after linking so #64 routes ship immediately.

After this, every merge to `main` that changes backend (or the whole repo, depending on watch settings) triggers a new Railway deploy.

## Alternative: Deploy from GHCR image

CI already publishes:

- `ghcr.io/pleasemahobo/bhudi-online-api:latest`
- `ghcr.io/pleasemahobo/bhudi-online-api:<git-sha>`

1. Service source → **Docker Image**
2. Image: `ghcr.io/pleasemahobo/bhudi-online-api`
3. Tag: `latest` (or pin to SHA for safer rollouts)
4. Ensure Railway can pull from GHCR (registry credentials / public package as configured)

Image push succeeds in CI even when Railway is not linked; you must still wire the service to pull and restart.

## Verify new MSP routes

```bash
# Expect 401/403/422 after auth middleware — not 404
curl -sS -X POST https://bhudi-online-production.up.railway.app/api/v1/msp/customers/wizard \
  -H 'Content-Type: application/json' -d '{}'
```

- **404** → service still on old revision; redeploy from `main` or `:latest`.
- **401/403/422** → route is live.

## Frontend

Vercel deploys independently. API base defaults to Railway
(`NEXT_PUBLIC_API_URL` / `https://bhudi-online-production.up.railway.app`).
