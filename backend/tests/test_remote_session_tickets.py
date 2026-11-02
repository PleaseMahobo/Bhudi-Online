from __future__ import annotations

import time
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


TEST_AGENT_ID = "55555555-5555-4555-8555-55555555555e"


def _build_client() -> tuple[TestClient, User]:
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

    db = session_factory()
    tenant = Tenant(id=uuid.uuid4(), name="Ticket Test Tenant", created_at=datetime.now(timezone.utc))
    db.add(tenant)
    db.flush()
    db.add(
        Agent(
            id=uuid.UUID(TEST_AGENT_ID),
            tenant_id=tenant.id,
            hostname="ticket-agent-01",
            platform="windows",
            registration_state="approved",
            approved=True,
            enabled=True,
            revoked=False,
            quarantined=False,
            command_timeout=300,
            enrollment_token="test-ticket-agent-token",
        )
    )
    db.commit()
    db.close()
    import app.database.session as db_session
    db_session.SessionLocal = session_factory

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(remote_access.router)
    app.dependency_overrides[get_db] = override_get_db
    test_user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email="tickets@example.com", active=True, mfa_enabled=True
    )
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_mfa_for_actions] = lambda: test_user
    return TestClient(app), test_user


def _queue_desktop(client: TestClient) -> dict:
    response = client.post(
        "/remote-access/desktop",
        json={"agent_id": TEST_AGENT_ID, "session_mode": "control", "display_protocol": "native"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_session_create_issues_purpose_scoped_tickets() -> None:
    client, _ = _build_client()
    payload = _queue_desktop(client)

    assert payload["dashboard_ticket"]
    assert payload["input_ticket"]
    assert payload["agent_ticket"]
    assert payload["payload"]["input_token"] == payload["input_ticket"]
    assert payload["payload"]["agent_ticket"] == payload["agent_ticket"]
    assert payload["payload"]["dashboard_ticket"] == payload["dashboard_ticket"]
    assert len({payload["dashboard_ticket"], payload["input_ticket"], payload["agent_ticket"]}) == 3


def test_dashboard_and_agent_require_matching_tickets() -> None:
    client, _ = _build_client()
    payload = _queue_desktop(client)
    session_id = payload["session_id"]
    dashboard_ticket = payload["dashboard_ticket"]
    agent_ticket = payload["agent_ticket"]

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?ticket={agent_ticket}"
    ) as ws:
        assert ws.receive_json()["type"] == "error"

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}?ticket={dashboard_ticket}&agent_token=test-ticket-agent-token"
    ) as ws:
        assert ws.receive_json()["type"] == "error"

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?ticket={dashboard_ticket}"
    ) as ws:
        assert ws.receive_json()["type"] == "session_state"
    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}?ticket={agent_ticket}&agent_token=test-ticket-agent-token"
    ) as ws:
        assert ws.receive_json()["type"] == "session_attached"


def test_agent_path_agent_id_mismatch_rejected() -> None:
    client, _ = _build_client()
    payload = _queue_desktop(client)
    session_id = payload["session_id"]
    agent_ticket = payload["agent_ticket"]
    other_agent = "66666666-6666-4666-8666-66666666666f"

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{other_agent}?ticket={agent_ticket}&agent_token=test-ticket-agent-token"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "mismatch" in msg["message"].lower() or "not found" in msg["message"].lower() or "credential" in msg["message"].lower()


def test_close_session_revokes_tickets() -> None:
    client, _ = _build_client()
    payload = _queue_desktop(client)
    session_id = payload["session_id"]
    dashboard_ticket = payload["dashboard_ticket"]
    agent_ticket = payload["agent_ticket"]
    input_ticket = payload["input_ticket"]

    close = client.post(f"/remote-access/sessions/{session_id}/close")
    assert close.status_code == 200
    assert close.json()["status"] == "closed"

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?ticket={dashboard_ticket}"
    ) as ws:
        assert ws.receive_json()["type"] == "error"
    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}?ticket={agent_ticket}&agent_token=test-ticket-agent-token"
    ) as ws:
        assert ws.receive_json()["type"] == "error"
    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?channel=input&token={input_ticket}"
    ) as ws:
        assert ws.receive_json()["type"] == "error"


def test_expired_ticket_is_rejected() -> None:
    client, _ = _build_client()
    state = remote_session_manager.create_session(
        agent_id=TEST_AGENT_ID,
        session_type="desktop",
        tenant_id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        ticket_ttl_seconds=1,
    )
    ticket = state.dashboard_ticket.token
    time.sleep(1.1)
    assert state.dashboard_ticket is not None
    assert not state.dashboard_ticket.is_valid()

    with client.websocket_connect(
        f"/remote-access/sessions/{state.session_id}/dashboard?ticket={ticket}"
    ) as ws:
        assert ws.receive_json()["type"] == "error"


def test_owner_session_get_returns_tickets() -> None:
    client, _ = _build_client()
    payload = _queue_desktop(client)
    session_id = payload["session_id"]

    response = client.get(f"/remote-access/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["dashboard_ticket"] == payload["dashboard_ticket"]
    assert body["input_ticket"] == payload["input_ticket"]
    assert body["agent_ticket"] == payload["agent_ticket"]
