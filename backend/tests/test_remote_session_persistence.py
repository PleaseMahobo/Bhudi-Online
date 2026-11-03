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
from app.core.access_tiers import require_mfa_for_actions
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.agent import Agent
from app.models.tenant import Tenant
from app.models.user import User
from app.services.remote_session_manager import remote_session_manager


TEST_AGENT_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
TEST_AGENT_TOKEN = "persist-agent-token"


def _build_client() -> TestClient:
    remote_session_manager._sessions.clear()
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    bootstrap.engine = engine
    bootstrap.SessionLocal = session_factory
    bootstrap._bootstrap_metadata_for_engine().create_all(bind=engine)

    import app.database.session as db_session

    db_session.SessionLocal = session_factory

    db = session_factory()
    tenant = Tenant(id=uuid.uuid4(), name="Persist Tenant", created_at=datetime.now(timezone.utc))
    db.add(tenant)
    db.flush()
    db.add(
        Agent(
            id=uuid.UUID(TEST_AGENT_ID),
            tenant_id=tenant.id,
            hostname="persist-agent",
            platform="windows",
            registration_state="approved",
            approved=True,
            enabled=True,
            revoked=False,
            quarantined=False,
            command_timeout=300,
            enrollment_token=TEST_AGENT_TOKEN,
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(remote_access.router)
    app.dependency_overrides[get_db] = override_get_db
    user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email="persist@example.com", active=True, mfa_enabled=True
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_mfa_for_actions] = lambda: user
    return TestClient(app)


def test_session_rehydrates_after_worker_memory_loss() -> None:
    client = _build_client()
    response = client.post(
        "/remote-access/desktop",
        json={"agent_id": TEST_AGENT_ID, "session_mode": "control", "display_protocol": "native"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    session_id = payload["session_id"]
    dashboard_ticket = payload["dashboard_ticket"]
    agent_ticket = payload["agent_ticket"]

    # Simulate worker process restart: drop process-local state only.
    remote_session_manager._sessions.clear()
    assert session_id not in remote_session_manager._sessions

    # Durable row should rehydrate.
    restored = remote_session_manager.get_session(session_id)
    assert restored is not None
    assert restored.session_id == session_id
    assert restored.agent_credential_bound is False
    assert restored.dashboard_ticket is not None
    assert restored.dashboard_ticket.token == dashboard_ticket

    http = client.get(f"/remote-access/sessions/{session_id}")
    assert http.status_code == 200
    assert http.json()["dashboard_ticket"] == dashboard_ticket

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?ticket={dashboard_ticket}"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "session_state"

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}"
        f"?ticket={agent_ticket}&agent_token={TEST_AGENT_TOKEN}"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "session_attached"
        assert msg["session"]["agent_credential_bound"] is True

    remote_session_manager._sessions.clear()
