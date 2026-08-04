from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import automation
from app.core.bootstrap import _bootstrap_metadata_for_engine
from app.database.session import get_db


def test_automation_run_creates_script_task_and_log() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _bootstrap_metadata_for_engine().create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(automation.router, prefix="/automation")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post(
        "/automation/automation/run",
        json={
            "device_id": "00000000-0000-0000-0000-000000000001",
            "script_name": "reboot-check",
            "content": "Write-Host 'ok'",
            "parameters": {"mode": "check"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["data"]["task_id"]


def test_incident_run_updates_response_action_state() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _bootstrap_metadata_for_engine().create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(automation.router, prefix="/automation")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    create_response = client.post(
        "/automation/automation/run",
        json={
            "device_id": "00000000-0000-0000-0000-000000000002",
            "script_name": "incident-check",
            "content": "Write-Host 'incident'",
            "incident_id": "00000000-0000-0000-0000-000000000010",
            "response_action": "containment",
        },
    )

    assert create_response.status_code == 200
    created_payload = create_response.json()
    task_id = created_payload["data"]["task_id"]

    update_response = client.post(
        f"/automation/automation/tasks/{task_id}/state",
        json={"status": "succeeded", "output": "completed", "exit_code": 0},
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["data"]["response_action_status"] == "succeeded"
