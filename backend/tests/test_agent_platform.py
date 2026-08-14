from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import agent_runtime
from app.core.access_tiers import require_mfa_for_actions


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agent_runtime.router)
    app.dependency_overrides[require_mfa_for_actions] = lambda: object()
    return TestClient(app)


def test_agent_platform_exposes_agent_details_and_command_history() -> None:
    client = _build_client()
    enroll_response = client.post("/runtime/enroll", json={"hostname": "agent-01", "agent_version": "1.2.3", "platform": "linux", "enrollment_secret": "phase-3-test"})
    assert enroll_response.status_code == 200
    body = enroll_response.json()
    agent_id = body["agent_id"]
    agent_token = body["agent_token"]

    details_response = client.get(f"/runtime/agents/{agent_id}")
    assert details_response.status_code == 200
    assert details_response.json()["agent_id"] == agent_id

    queue_response = client.post(f"/runtime/agents/{agent_id}/commands", json={"command": "echo hello", "shell": True})
    assert queue_response.status_code == 200
    command_id = queue_response.json()["command_id"]

    pending_response = client.get(f"/runtime/agents/{agent_id}/commands/pending", params={"agent_token": agent_token})
    assert pending_response.status_code == 200
    assert pending_response.json()["commands"][0]["command_id"] == command_id

    result_response = client.post(f"/runtime/agents/{agent_id}/commands/{command_id}/result", params={"agent_token": agent_token}, json={"exit_code": 0, "stdout": "hello", "stderr": ""})
    assert result_response.status_code == 200

    history_response = client.get(f"/runtime/agents/{agent_id}/commands")
    assert history_response.status_code == 200
    commands = history_response.json()["commands"]
    assert len(commands) == 1
    assert commands[0]["status"] == "completed"


def test_agent_commands_support_acknowledgement_and_retry_tracking() -> None:
    client = _build_client()
    body = client.post("/runtime/enroll", json={"hostname": "agent-02", "agent_version": "1.0.0", "platform": "windows"}).json()
    agent_id = body["agent_id"]
    agent_token = body["agent_token"]

    command_id = client.post(f"/runtime/agents/{agent_id}/commands", json={"command": "python -c 'exit(1)'", "shell": True}).json()["command_id"]
    ack_response = client.post(f"/runtime/agents/{agent_id}/commands/{command_id}/ack", params={"agent_token": agent_token}, json={"status": "running"})
    assert ack_response.status_code == 200
    assert ack_response.json()["acknowledged"] is True

    result_response = client.post(f"/runtime/agents/{agent_id}/commands/{command_id}/result", params={"agent_token": agent_token}, json={"exit_code": 1, "stdout": "", "stderr": "boom"})
    assert result_response.status_code == 200
    command = client.get(f"/runtime/agents/{agent_id}/commands").json()["commands"][0]
    assert command["status"] == "pending"
    assert command["retry_count"] == 1


def test_agent_stream_endpoint_accepts_connections() -> None:
    client = _build_client()
    agent_id = client.post("/runtime/enroll", json={"hostname": "agent-03", "agent_version": "1.0.0", "platform": "linux"}).json()["agent_id"]
    with client.websocket_connect(f"/runtime/agents/{agent_id}/stream") as websocket:
        payload = websocket.receive_json()
        assert payload["event"] == "connected"
