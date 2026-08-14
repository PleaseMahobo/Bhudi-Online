from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import agent_runtime
from app.core.access_tiers import require_mfa_for_actions


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(agent_runtime.router)
    app.dependency_overrides[require_mfa_for_actions] = lambda: object()
    return TestClient(app)


def test_enrollment_heartbeat_command_result_pipeline() -> None:
    client = _client()
    enrolled = client.post(
        "/runtime/enroll",
        json={
            "hostname": "pipeline-agent",
            "agent_version": "1.2.0",
            "platform": "linux",
        },
    )
    assert enrolled.status_code == 200
    identity = enrolled.json()

    heartbeat = client.post(
        "/runtime/heartbeat",
        json={
            "agent_id": identity["agent_id"],
            "agent_token": identity["agent_token"],
            "status": "online",
            "cpu_percent": 22.5,
            "memory_percent": 41.0,
            "disk_percent": 55.0,
            "hostname": "pipeline-agent",
        },
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["ok"] is True

    queued = client.post(
        f"/runtime/agents/{identity['agent_id']}/commands",
        json={"command": "install nginx", "shell": True},
    )
    assert queued.status_code == 200
    command = queued.json()
    assert command["execution_profile"]["platform_family"] == "linux"
    assert "apt-get install -y nginx" in command["execution_profile"]["translated_command"]

    pending = client.get(
        f"/runtime/agents/{identity['agent_id']}/commands/pending",
        params={"agent_token": identity["agent_token"]},
    )
    assert pending.status_code == 200
    assert pending.json()["commands"][0]["status"] == "dispatched"

    completed = client.post(
        f"/runtime/agents/{identity['agent_id']}/commands/{command['command_id']}/result",
        params={"agent_token": identity["agent_token"]},
        json={"exit_code": 0, "stdout": "installed", "stderr": ""},
    )
    assert completed.status_code == 200
    assert completed.json()["command"]["status"] == "completed"

    details = client.get(f"/runtime/agents/{identity['agent_id']}")
    assert details.status_code == 200
    assert details.json()["status"] == "online"
    assert details.json()["commands_completed"] == 1
    assert details.json()["cpu_percent"] == 22.5
