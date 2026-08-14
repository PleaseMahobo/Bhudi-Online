from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import agent_runtime
from app.core.access_tiers import require_mfa_for_actions


def test_agent_command_callbacks_reject_missing_or_invalid_tokens() -> None:
    app = FastAPI()
    app.include_router(agent_runtime.router)
    app.dependency_overrides[require_mfa_for_actions] = lambda: object()
    client = TestClient(app)

    identity = client.post("/runtime/enroll", json={"hostname": "secure-agent", "platform": "linux"}).json()
    agent_id = identity["agent_id"]
    command = client.post(f"/runtime/agents/{agent_id}/commands", json={"command": "echo secure"}).json()
    command_id = command["command_id"]

    assert client.get(f"/runtime/agents/{agent_id}/commands/pending").status_code == 401
    assert client.get(f"/runtime/agents/{agent_id}/commands/pending", params={"agent_token": "wrong"}).status_code == 401
    assert client.post(f"/runtime/agents/{agent_id}/commands/{command_id}/ack", json={"status": "running"}).status_code == 401
    assert client.post(f"/runtime/agents/{agent_id}/commands/{command_id}/result", json={"exit_code": 0}).status_code == 401
