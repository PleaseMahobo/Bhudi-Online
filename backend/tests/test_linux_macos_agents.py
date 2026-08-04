from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import agent_runtime


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agent_runtime.router)
    return TestClient(app)


def test_linux_and_macos_agents_are_classified_with_platform_metadata() -> None:
    client = _build_client()

    for platform_name in ["linux", "darwin"]:
        response = client.post(
            "/runtime/enroll",
            json={"hostname": f"{platform_name}-agent", "agent_version": "1.0.0", "platform": platform_name},
        )
        assert response.status_code == 200
        payload = response.json()
        agent_id = payload["agent_id"]

        details = client.get(f"/runtime/agents/{agent_id}")
        assert details.status_code == 200
        assert details.json()["platform"] == platform_name

        metadata = client.get(f"/runtime/agents/{agent_id}/platform")
        assert metadata.status_code == 200
        assert metadata.json()["platform_family"] in {"linux", "macos"}
