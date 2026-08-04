from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import agent_runtime


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agent_runtime.router)
    return TestClient(app)


def test_common_package_tasks_translate_to_os_specific_commands() -> None:
    client = _build_client()

    cases = [
        ("linux", "install nginx", "sudo apt-get update && sudo apt-get install -y nginx"),
        ("linux", "update nginx", "sudo apt-get update && sudo apt-get install -y nginx"),
        ("linux", "uninstall nginx", "sudo apt-get remove -y nginx"),
        ("darwin", "install nginx", "brew update && brew install nginx"),
        ("darwin", "update nginx", "brew update && brew upgrade nginx"),
        ("darwin", "uninstall nginx", "brew uninstall nginx"),
    ]

    for platform_name, raw_command, expected in cases:
        response = client.post(
            "/runtime/enroll",
            json={"hostname": f"{platform_name}-agent", "agent_version": "1.0.0", "platform": platform_name},
        )
        agent_id = response.json()["agent_id"]
        queue = client.post(f"/runtime/agents/{agent_id}/commands", json={"command": raw_command, "shell": True})
        command_id = queue.json()["command_id"]
        details = client.get(f"/runtime/agents/{agent_id}/commands/{command_id}")
        payload = details.json()
        assert payload["execution_profile"]["translated_command"] == expected
