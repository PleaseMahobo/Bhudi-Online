from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.executor import execute_command_record
from app.api.v1.endpoints import agent_commands, remote_access
from app.core import bootstrap
from app.database.session import get_db
from app.models.agent import Agent


TEST_AGENT_ID = "22222222-2222-4222-8222-22222222222b"
TEST_AGENT_TOKEN = "test-agent-token-2222"


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    bootstrap.engine = engine
    bootstrap.SessionLocal = session_factory
    bootstrap._bootstrap_metadata_for_engine().create_all(bind=engine)

    session = session_factory()
    session.add(
        Agent(
            id=uuid.UUID(TEST_AGENT_ID),
            hostname="remote-agent-02",
            platform="windows",
            approved=True,
            enabled=True,
            command_timeout=300,
            enrollment_token=TEST_AGENT_TOKEN,
        )
    )
    session.commit()
    session.close()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(remote_access.router)
    app.include_router(agent_commands.router)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _agent_params() -> dict[str, str]:
    return {"agent_token": TEST_AGENT_TOKEN}


def _execute_next_command(client: TestClient, *, platform_name: str) -> tuple[dict, dict]:
    queued = client.get(f"/agent/{TEST_AGENT_ID}/commands", params=_agent_params())
    assert queued.status_code == 200
    command = queued.json()[0]
    command_id = command["command_id"]

    sent = client.post(f"/agent/{TEST_AGENT_ID}/commands/{command_id}/sent", params=_agent_params())
    assert sent.status_code == 200

    result = execute_command_record(command, platform_name=platform_name)
    if result["exit_code"] == 0:
        completion = client.post(
            f"/agent/{TEST_AGENT_ID}/commands/{command_id}/completed",
            params=_agent_params(),
            json=result,
        )
    else:
        completion = client.post(
            f"/agent/{TEST_AGENT_ID}/commands/{command_id}/failed",
            params=_agent_params(),
            json={"message": result.get("stderr") or result.get("stdout") or "execution failed"},
        )
    assert completion.status_code == 200

    status = client.get(f"/remote-access/operations/{command_id}")
    assert status.status_code == 200
    return command, status.json()


def test_remote_terminal_executes_end_to_end_for_macos() -> None:
    client = _build_client()
    response = client.post(
        "/remote-access/terminal",
        json={"agent_id": TEST_AGENT_ID, "shell": "zsh", "working_directory": "/tmp", "interactive": True},
    )
    assert response.status_code == 201
    command, status_payload = _execute_next_command(client, platform_name="darwin")
    assert command["command_type"] == "remote.terminal.start"
    assert status_payload["status"] == "completed"
    assert status_payload["command_type"] == "remote.terminal.start"


def test_file_browser_executes_end_to_end_for_linux() -> None:
    client = _build_client()
    with tempfile.TemporaryDirectory() as temp_dir:
        target_path = str(Path(temp_dir) / "artifact.txt")
        response = client.post(
            "/remote-access/file-browser",
            json={"agent_id": TEST_AGENT_ID, "operation": "upload", "path": target_path, "content_b64": "aGVsbG8=", "overwrite": True},
        )
        assert response.status_code == 201
        _, status_payload = _execute_next_command(client, platform_name="linux")
        assert status_payload["status"] == "completed"
        assert Path(target_path).read_text(encoding="utf-8") == "hello"


def test_safe_mode_reboot_executes_end_to_end_for_windows_dry_run() -> None:
    client = _build_client()
    os.environ.pop("BHUDI_ALLOW_POWER_ACTIONS", None)
    response = client.post(
        "/remote-access/safe-mode-reboot",
        json={"agent_id": TEST_AGENT_ID, "with_networking": True, "delay_seconds": 5},
    )
    assert response.status_code == 201
    _, status_payload = _execute_next_command(client, platform_name="win32")
    assert status_payload["status"] == "completed"
    assert status_payload["requires_reboot"] is True


def test_registry_editor_fails_cleanly_on_linux() -> None:
    client = _build_client()
    response = client.post(
        "/remote-access/registry",
        json={"agent_id": TEST_AGENT_ID, "operation": "get", "hive": "HKLM", "key_path": "Software\\Bhudi", "value_name": "InstallPath"},
    )
    assert response.status_code == 201
    _, status_payload = _execute_next_command(client, platform_name="linux")
    assert status_payload["status"] == "failed"
