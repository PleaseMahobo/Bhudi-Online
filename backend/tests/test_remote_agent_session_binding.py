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


TEST_AGENT_ID = "77777777-7777-4777-8777-77777777777a"
TEST_AGENT_TOKEN = "binding-agent-token-7777"


def _build_client(*, enrollment_token: str | None = TEST_AGENT_TOKEN, **agent_overrides) -> TestClient:
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

    import app.database.session as db_session

    db_session.SessionLocal = session_factory

    db = session_factory()
    tenant = Tenant(id=uuid.uuid4(), name="Binding Tenant", created_at=datetime.now(timezone.utc))
    db.add(tenant)
    db.flush()
    agent_kwargs = dict(
        id=uuid.UUID(TEST_AGENT_ID),
        tenant_id=tenant.id,
        hostname="bind-agent-01",
        platform="windows",
        registration_state="approved",
        approved=True,
        enabled=True,
        revoked=False,
        quarantined=False,
        command_timeout=300,
        enrollment_token=enrollment_token,
    )
    agent_kwargs.update(agent_overrides)
    db.add(Agent(**agent_kwargs))
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
    test_user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email="bind@example.com", active=True, mfa_enabled=True
    )
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_mfa_for_actions] = lambda: test_user
    return TestClient(app)


def _queue(client: TestClient) -> dict:
    response = client.post(
        "/remote-access/desktop",
        json={"agent_id": TEST_AGENT_ID, "session_mode": "control", "display_protocol": "native"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_agent_stream_requires_agent_token() -> None:
    client = _build_client()
    payload = _queue(client)
    session_id = payload["session_id"]
    agent_ticket = payload["agent_ticket"]

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}?ticket={agent_ticket}"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "credential" in msg["message"].lower()


def test_agent_stream_rejects_invalid_agent_token() -> None:
    client = _build_client()
    payload = _queue(client)
    session_id = payload["session_id"]
    agent_ticket = payload["agent_ticket"]

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}"
        f"?ticket={agent_ticket}&agent_token=wrong-token"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "invalid" in msg["message"].lower()


def test_agent_stream_accepts_bound_credential() -> None:
    client = _build_client()
    payload = _queue(client)
    session_id = payload["session_id"]
    agent_ticket = payload["agent_ticket"]

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}"
        f"?ticket={agent_ticket}&agent_token={TEST_AGENT_TOKEN}"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "session_attached"
        assert msg["session"]["agent_credential_bound"] is True


def test_quarantined_agent_cannot_bind_session() -> None:
    """Quarantined agents must be rejected before a remote session is issued."""
    client = _build_client(quarantined=True)
    response = client.post(
        "/remote-access/desktop",
        json={"agent_id": TEST_AGENT_ID, "session_mode": "control", "display_protocol": "native"},
    )
    assert response.status_code == 403, response.text
    detail = response.json().get("detail", "")
    assert "quarantine" in str(detail).lower()


def test_agent_message_with_foreign_session_id_is_dropped() -> None:
    client = _build_client()
    payload = _queue(client)
    session_id = payload["session_id"]
    dashboard_ticket = payload["dashboard_ticket"]
    agent_ticket = payload["agent_ticket"]

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?ticket={dashboard_ticket}"
    ) as dashboard_ws:
        dashboard_ws.receive_json()
        with client.websocket_connect(
            f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}"
            f"?ticket={agent_ticket}&agent_token={TEST_AGENT_TOKEN}"
        ) as agent_ws:
            agent_ws.receive_json()
            dashboard_ws.receive_json()

            agent_ws.send_json(
                {"type": "output", "session_id": "not-this-session", "data": "leaked"}
            )
            agent_ws.send_json(
                {"type": "output", "session_id": session_id, "data": "bound-ok"}
            )
            output = dashboard_ws.receive_json()
            assert output["type"] == "output"
            assert output["data"] == "bound-ok"


def test_dashboard_message_with_foreign_session_id_is_dropped() -> None:
    client = _build_client()
    payload = _queue(client)
    session_id = payload["session_id"]
    dashboard_ticket = payload["dashboard_ticket"]
    agent_ticket = payload["agent_ticket"]

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?ticket={dashboard_ticket}"
    ) as dashboard_ws:
        dashboard_ws.receive_json()
        with client.websocket_connect(
            f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}"
            f"?ticket={agent_ticket}&agent_token={TEST_AGENT_TOKEN}"
        ) as agent_ws:
            agent_ws.receive_json()
            dashboard_ws.receive_json()

            dashboard_ws.send_json({"type": "pointer", "session_id": "other", "x": 1, "y": 2})
            dashboard_ws.send_json({"type": "pointer", "session_id": session_id, "x": 3, "y": 4})
            msg = agent_ws.receive_json()
            assert msg["type"] == "dashboard_message"
            assert msg["payload"]["x"] == 3
            assert msg["payload"]["y"] == 4
