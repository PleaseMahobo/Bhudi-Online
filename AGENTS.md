# Agent & AI assistant guide

Purpose: Provide concise, actionable guidance for AI coding agents to get productive in this repository.

Quick start (backend)

- **Create venv & install:** `python -m venv .venv` then `\.venv\Scripts\activate` (Windows) and `pip install -r backend/requirements.txt`.
- **Run dev server:** from `backend/` run `uvicorn app.main:app --reload --port 8000`.
- **Docker:** see `backend/Dockerfile` for containerized run (exposes port 8000).

Quick start (frontend)

- **Install & dev:** `cd frontend` then `npm install` and `npm run dev` (Next.js app).
- Frontend agent rules and notes: see `frontend/AGENTS.md` and `frontend/CLAUDE.md`.

Database & migrations

- Migrations live in `backend/alembic/` and `backend/alembic.ini` — run Alembic from the `backend/` folder when a Postgres DB is available.
- There are helper scripts: `backend/init_db.py` and top-level `init_db.py` for local DB initialization.

Agent runtime & tooling

- The RMM agent code is in `agent/` (see `agent/requirements.txt`). The `rmm/rmm_agent.py` file contains an alternate agent script.
- Use `python -m` or run the individual scripts inside `agent/` for local testing.

Useful files (links)

- Backend entrypoint: [backend/app/main.py](backend/app/main.py)
- Backend requirements: [backend/requirements.txt](backend/requirements.txt)
- Backend Dockerfile: [backend/Dockerfile](backend/Dockerfile)
- Frontend package.json: [frontend/package.json](frontend/package.json)
- Frontend agent rules: [frontend/AGENTS.md](frontend/AGENTS.md)

Notes for AI agents

- Link, don't duplicate: prefer linking repository docs rather than copying them into this file.
- Preserve existing content: if you update docs, merge instead of replacing.
- Environment: many components rely on environment variables and external services (Postgres, Supabase). Do not run migrations or start services that require external systems without test doubles or explicit user permission.

Next suggested customizations

- Add a `.github/copilot-instructions.md` or expand this file with short per-area instructions (backend/frontend/agent) if you want role-specific guidance.
- Consider small skills for common tasks: `create-migration`, `run-backend-dev`, `run-frontend-dev`.
