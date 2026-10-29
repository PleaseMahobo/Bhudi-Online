from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import remote_access
from app.core import bootstrap
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.access_tiers import require_mfa_for_actions
from app.models.user import User
from app.models.agent import Agent
from app.models.tenant import Tenant
from app.models.agent_command import AgentCommand
from app.services.remote_session_manager import remote_session_manager


TEST_AGENT_ID = "11111111-1111-4111-8111-11111111111a"


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

    agent_id = uuid.UUID(TEST_AGENT_ID)

    session = session_factory()
    tenant = Tenant(id=uuid.uuid4(), name="Remote Access Test Tenant", created_at=datetime.now(timezone.utc))
    session.add(tenant)
    session.flush()
    session.add(
        Agent(
            id=agent_id,
            tenant_id=tenant.id,
            hostname="remote-agent-01",
            platform="windows",
            registration_state="approved",
            approved=True,
            enabled=True,
            revoked=False,
            command_timeout=300,
        )
    )
    session.commit()
    # Verify the fixture's persisted authorization state before requests run.
    persisted_agent = session.get(Agent, agent_id if "agent_id" in locals() else uuid.UUID(TEST_AGENT_ID))
    assert persisted_agent is not None
    session.refresh(persisted_agent)
    assert persisted_agent.id == uuid.UUID(TEST_AGENT_ID)
    assert persisted_agent.tenant_id == tenant.id
    assert persisted_agent.revoked is False
    assert persisted_agent.revoked_at is None
    assert persisted_agent.revocation_reason is None
    assert persisted_agent.enabled is True
    assert persisted_agent.quarantined is False
    assert persisted_agent.registration_state == "approved"
    session.close()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(remote_access.router)
    app.dependency_overrides[get_db] = override_get_db
    test_user = User(id=uuid.uuid4(), tenant_id=tenant.id, email="test@example.com", active=True, mfa_enabled=True)
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_mfa_for_actions] = lambda: test_user
    return TestClient(app)


def test_remote_access_capabilities_and_desktop_queue() -> None:
    client = _build_client()

    capabilities_response = client.get("/remote-access/capabilities")
    assert capabilities_response.status_code == 200
    operations = {item["operation"] for item in capabilities_response.json()}
    assert "remote_desktop" in operations
    assert "safe_mode_reboot" in operations

    queue_response = client.post(
        "/remote-access/desktop",
        json={
            "agent_id": TEST_AGENT_ID,
            "session_mode": "control",
            "display_protocol": "rdp",
            "consent_required": True,
        },
    )

    assert queue_response.status_code == 201, queue_response.text
    payload = queue_response.json()
    assert payload["operation"] == "remote_desktop"
    assert payload["command_type"] == "remote.desktop.start"
    assert payload["payload"]["display_protocol"] == "rdp"
    assert payload["status"] == "pending"
    assert payload["session_id"]
    assert payload["session_status"] == "pending"
    assert payload["stream_path"].endswith(f"/remote-access/sessions/{payload['session_id']}/dashboard")

    status_response = client.get(f"/remote-access/operations/{payload['command_id']}")
    assert status_response.status_code == 200
    assert status_response.json()["command_id"] == payload["command_id"]


def test_remote_access_reboot_and_registry_validation() -> None:
    client = _build_client()

    reboot_response = client.post(
        "/remote-access/safe-mode-reboot",
        json={
            "agent_id": TEST_AGENT_ID,
            "with_networking": True,
            "delay_seconds": 15,
        },
    )

    assert reboot_response.status_code == 201, reboot_response.text
    reboot_payload = reboot_response.json()
    assert reboot_payload["requires_reboot"] is True
    assert reboot_payload["payload"]["with_networking"] is True
    assert reboot_payload["command_type"] == "remote.safe_mode_reboot"

    invalid_registry_response = client.post(
        "/remote-access/registry",
        json={
            "agent_id": TEST_AGENT_ID,
            "operation": "set",
            "hive": "HKLM",
            "key_path": "Software\\Bhudi",
        },
    )

    assert invalid_registry_response.status_code == 422


def test_remote_access_rejects_authenticated_user_without_tenant() -> None:
    client = _build_client()
    unscoped_user = User(
        id=uuid.uuid4(),
        email="unscoped@example.com",
        active=True,
        mfa_enabled=True,
    )
    client.app.dependency_overrides[require_mfa_for_actions] = lambda: unscoped_user

    response = client.post(
        "/remote-access/desktop",
        json={"agent_id": TEST_AGENT_ID},
    )

    assert response.status_code == 403
    assert "Tenant association required" in response.json()["detail"]


def test_remote_access_file_browser_upload_requires_content() -> None:
    client = _build_client()

    invalid_upload_response = client.post(
        "/remote-access/file-browser",
        json={
            "agent_id": TEST_AGENT_ID,
            "operation": "upload",
            "path": "C:/Temp/tool.txt",
        },
    )

    assert invalid_upload_response.status_code == 422

    valid_upload_response = client.post(
        "/remote-access/file-browser",
        json={
            "agent_id": TEST_AGENT_ID,
            "operation": "upload",
            "path": "C:/Temp/tool.txt",
            "content_b64": "dGVzdA==",
            "overwrite": True,
        },
    )

    assert valid_upload_response.status_code == 201, valid_upload_response.text
    payload = valid_upload_response.json()
    assert payload["command_type"] == "remote.file_browser"
    assert payload["payload"]["operation"] == "upload"

def test_remote_access_rejects_cross_tenant_dispatch_without_side_effects() -> None:
    client = _build_client()
    other_tenant_user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="other-tenant@example.com",
        active=True,
        mfa_enabled=True,
    )
    client.app.dependency_overrides[require_mfa_for_actions] = lambda: other_tenant_user

    existing_session_ids = set(remote_session_manager._sessions)
    db = bootstrap.SessionLocal()
    try:
        commands_before = db.query(AgentCommand).count()
    finally:
        db.close()

    response = client.post("/remote-access/desktop", json={"agent_id": TEST_AGENT_ID})

    assert response.status_code == 403
    assert "authorized tenant" in response.json()["detail"].lower()
    assert set(remote_session_manager._sessions) == existing_session_ids
    db = bootstrap.SessionLocal()
    try:
        assert db.query(AgentCommand).count() == commands_before
    finally:
        db.close()
