from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import agent_runtime


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agent_runtime.router)
    return TestClient(app)


def test_linux_and_macos_commands_use_platform_specific_defaults() -> None:
    client = _build_client()

    for platform_name, expected_shell, expected_package_manager in [("linux", "/bin/bash", "apt"), ("darwin", "/bin/zsh", "brew")]:
        response = client.post(
            "/runtime/enroll",
            json={"hostname": f"{platform_name}-agent", "agent_version": "1.0.0", "platform": platform_name},
        )
        agent_id = response.json()["agent_id"]

        queue = client.post(
            f"/runtime/agents/{agent_id}/commands",
            json={"command": "install package", "shell": True},
        )
        command_id = queue.json()["command_id"]

        details = client.get(f"/runtime/agents/{agent_id}/commands/{command_id}")
        payload = details.json()
        assert payload["shell"] is True
        assert payload["execution_profile"]["default_shell"] == expected_shell
        assert payload["execution_profile"]["package_manager"] == expected_package_manager
