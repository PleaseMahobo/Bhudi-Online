"""Minimal live HTTP server used by the real-agent E2E smoke test."""
from fastapi import FastAPI

from app.api.v1.endpoints import agent_runtime
from app.core.access_tiers import require_mfa_for_actions

app = FastAPI(title="Bhudi Agent E2E Harness")
app.include_router(agent_runtime.router, prefix="/api/v1")
app.dependency_overrides[require_mfa_for_actions] = lambda: object()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
