# Bhudi AI — deployment environment

Bhudi AI (side panel + `/ai` console) runs on the **API** service only.
Without these variables the UI shows **Guided mode** (heuristic playbooks).
With them configured and the API restarted, the panel shows **Live model**.

## Variables

| Variable | Required for live | Default | Description |
|----------|-------------------|---------|-------------|
| `AI_ENABLED` | yes | `false` | Set to `true`, `1`, `yes`, or `on` to allow outbound LLM calls |
| `AI_API_KEY` | yes | _(empty)_ | Bearer token for an OpenAI-compatible chat API |
| `AI_BASE_URL` | no | `https://api.openai.com/v1` | Base URL **without** trailing path beyond `/v1` |
| `AI_MODEL` | no | `gpt-4o-mini` | Model id sent in chat completions |

Used by:

- `POST /api/v1/ai/chat` — in-app assistant (`AssistantService`)
- `POST /api/v1/ai/root-cause`, `/script`, `/remediation`, … (`AIService`)

If `AI_ENABLED` is false **or** `AI_API_KEY` is empty, every call stays offline-safe (heuristic / `dry_run`).

Compatible providers: OpenAI, Azure OpenAI (set base URL to the Azure endpoint), Groq, OpenRouter, local gateways that implement `POST {AI_BASE_URL}/chat/completions`.

---

## Railway (production / staging API)

Hosting uses **Railway** for the FastAPI image (`railway.toml` / `railway.json` → `backend/Dockerfile`).

1. Open the **API** service (not the frontend).
2. **Variables** → add:

```text
AI_ENABLED=true
AI_API_KEY=sk-...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

3. Save. Railway redeploys or restart the service so the process picks up env.
4. Confirm:
   - Chat in the console → subtitle **Live model**
   - Or `POST /api/v1/ai/chat` with `{"message":"hello"}` and check `mode: "live"` in the JSON

**Staging:** use a **separate** key and optionally a cheaper model. Do not reuse production secrets if policies forbid it (`deploy/staging/README.md`).

**Security**

- Mark `AI_API_KEY` as a secret in Railway (never commit it).
- Restrict key scope / spend limits at the provider.
- Frontend never needs `AI_*`; only the API calls the model.

---

## Docker Compose (local / self-hosted)

`docker-compose.yml` passes AI settings into the `api` service.

Create a project `.env` (gitignored) next to compose:

```bash
AI_ENABLED=true
AI_API_KEY=sk-...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Then:

```bash
docker compose up -d api
# or recreate after env change:
docker compose up -d --force-recreate api
```

---

## Kubernetes

API pods load `envFrom: secretRef: bhudi-api-secrets`.
Include AI keys in that secret:

```bash
kubectl create secret generic bhudi-api-secrets \
  --from-literal=AI_ENABLED=true \
  --from-literal=AI_API_KEY='sk-...' \
  --from-literal=AI_BASE_URL='https://api.openai.com/v1' \
  --from-literal=AI_MODEL='gpt-4o-mini' \
  # ...plus DATABASE_URL, JWT_SECRET_KEY, etc.
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/bhudi-api
```

See `deploy/k8s/api-deployment.yaml`.

---

## Verify

| Check | Expected |
|-------|----------|
| UI assistant subtitle | **Live model** after a successful reply |
| Guided without key | **Guided mode** + playbook text |
| `/api/v1/ai/chat` response | `"mode": "live"` when configured |
| Provider outage | Falls back to heuristic (no hard crash) |

Disable live AI anytime: set `AI_ENABLED=false` or remove `AI_API_KEY` and restart the API.
