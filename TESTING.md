# Bhudi Online — Phase A+B Test Package

## What was fixed / added

### Phase A (backend boot)
- Fixed broken `backend/app/api/v1/router.py` (use-before-define + duplicates)
- Hardened `backend/app/main.py` (workers fail soft; WebSocket kept)
- Fixed `devices` endpoint → returns `{ "devices": [...] }`
- Added `device_repository.py`
- Import-safe stubs for empty endpoint modules
- **New** practical agent API under `/api/v1/runtime/*` (in-memory, always works)

### Phase B (unified agent)
- `agent/bhudi_agent.py` — single agent: enroll → heartbeat → poll → execute → result
- `agent/main.py` entrypoint
- `agent/agent_config.json` + env overrides

## Quick local test (runtime path — no Postgres required for /runtime)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn python-dotenv pydantic sqlalchemy requests
# Minimal: runtime endpoints don't need a live DB connection if those routes aren't hit.
# main.py imports SessionLocal which needs DATABASE_URL format valid at engine create.
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:5432/bhudi}"
export JWT_SECRET_KEY=dev-secret
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If Postgres is not running, SQLAlchemy may still create the engine; hitting auth/DB routes will fail.
**Runtime + devices/status work in-process without successful DB queries.**

In another terminal:

```bash
./scripts/smoke_test.sh http://127.0.0.1:8000
```

Agent:

```bash
cd agent
pip install -r requirements.txt
export BHUDI_SERVER_URL=http://127.0.0.1:8000
python main.py
```

Queue a command (after agent enrolled — check agent_identity.json):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/runtime/agents/$AGENT_ID/commands \
  -H 'Content-Type: application/json' \
  -d '{"command":"whoami"}'
```

## Railway

Set `DATABASE_URL`, `JWT_SECRET_KEY`, deploy `backend/`.
Point agent: `BHUDI_SERVER_URL=https://bhudi-online-production.up.railway.app`

## Known limits (next sprints)
- `/runtime` is in-memory (lost on restart) — wire to Agent/AgentCommand tables next
- Full `/api/v1/agents/*` still depends on complete AgentService + Postgres schema
- Frontend auth/CORS must be verified against Railway
- Double-prefix risk reduced for agents router; verify OpenAPI paths under /docs
