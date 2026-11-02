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
from app.models.agent_command import AgentCommand
from app.models.tenant import Tenant
from app.models.user import User
from app.services.remote_session_manager import remote_session_manager


TENANT_A_AGENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
TENANT_B_AGENT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"
AGENT_A_TOKEN = "tenant-a-agent-token"
AGENT_B_TOKEN = "tenant-b-agent-token"


def _reset_sessions() -> None:
    remote_session_manager._sessions.clear()


def _build_two_tenant_client() -> tuple[TestClient, User, User, uuid.UUID, uuid.UUID]:
    """Shared in-memory DB with two tenants, two agents, and two users."""
    _reset_sessions()
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
    tenant_a = Tenant(id=uuid.uuid4(), name="Tenant A", created_at=datetime.now(timezone.utc))
    tenant_b = Tenant(id=uuid.uuid4(), name="Tenant B", created_at=datetime.now(timezone.utc))
    db.add(tenant_a)
    db.add(tenant_b)
    db.flush()

    for agent_id, tenant, hostname, token in (
        (TENANT_A_AGENT_ID, tenant_a, "agent-a-01", AGENT_A_TOKEN),
        (TENANT_B_AGENT_ID, tenant_b, "agent-b-01", AGENT_B_TOKEN),
    ):
        db.add(
            Agent(
                id=uuid.UUID(agent_id),
                tenant_id=tenant.id,
                hostname=hostname,
                platform="windows",
                registration_state="approved",
                approved=True,
                enabled=True,
                revoked=False,
                quarantined=False,
                command_timeout=300,
                enrollment_token=token,
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

    user_a = User(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        email="a@example.com",
        active=True,
        mfa_enabled=True,
    )
    user_b = User(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        email="b@example.com",
        active=True,
        mfa_enabled=True,
    )

    app = FastAPI()
    app.include_router(remote_access.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[require_mfa_for_actions] = lambda: user_a
    return TestClient(app), user_a, user_b, tenant_a.id, tenant_b.id


def _as_user(client: TestClient, user: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: user
    client.app.dependency_overrides[require_mfa_for_actions] = lambda: user


def _queue_desktop(client: TestClient, agent_id: str) -> dict:
    response = client.post(
        "/remote-access/desktop",
        json={
            "agent_id": agent_id,
            "session_mode": "control",
            "display_protocol": "native",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_tenant_b_cannot_read_or_close_tenant_a_session() -> None:
    client, user_a, user_b, _tenant_a, _tenant_b = _build_two_tenant_client()
    try:
        _as_user(client, user_a)
        payload = _queue_desktop(client, TENANT_A_AGENT_ID)
        session_id = payload["session_id"]

        own = client.get(f"/remote-access/sessions/{session_id}")
        assert own.status_code == 200
        assert own.json()["session_id"] == session_id
        assert own.json().get("dashboard_ticket")

        _as_user(client, user_b)
        denied_get = client.get(f"/remote-access/sessions/{session_id}")
        assert denied_get.status_code == 404

        denied_close = client.post(f"/remote-access/sessions/{session_id}/close")
        assert denied_close.status_code == 404

        _as_user(client, user_a)
        still_open = client.get(f"/remote-access/sessions/{session_id}")
        assert still_open.status_code == 200
        assert still_open.json()["status"] != "closed"
    finally:
        _reset_sessions()


def test_tenant_b_cannot_dispatch_to_tenant_a_agent() -> None:
    client, user_a, user_b, _tenant_a, _tenant_b = _build_two_tenant_client()
    try:
        sessions_before = set(remote_session_manager._sessions)
        db = bootstrap.SessionLocal()
        try:
            commands_before = db.query(AgentCommand).count()
        finally:
            db.close()

        _as_user(client, user_b)
        response = client.post(
            "/remote-access/desktop",
            json={
                "agent_id": TENANT_A_AGENT_ID,
                "session_mode": "control",
                "display_protocol": "native",
            },
        )
        assert response.status_code == 403
        detail = response.json().get("detail", "").lower()
        assert "tenant" in detail or "authorized" in detail or "not found" in detail

        assert set(remote_session_manager._sessions) == sessions_before
        db = bootstrap.SessionLocal()
        try:
            assert db.query(AgentCommand).count() == commands_before
        finally:
            db.close()
    finally:
        _reset_sessions()


def test_foreign_agent_cannot_bind_with_stolen_tickets() -> None:
    """Agent B must not attach to tenant A session even if tickets leak."""
    client, user_a, _user_b, _tenant_a, _tenant_b = _build_two_tenant_client()
    try:
        _as_user(client, user_a)
        payload = _queue_desktop(client, TENANT_A_AGENT_ID)
        session_id = payload["session_id"]
        agent_ticket = payload["agent_ticket"]
        dashboard_ticket = payload["dashboard_ticket"]

        with client.websocket_connect(
            f"/remote-access/sessions/{session_id}/agent/{TENANT_B_AGENT_ID}"
            f"?ticket={agent_ticket}&agent_token={AGENT_B_TOKEN}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"

        with client.websocket_connect(
            f"/remote-access/sessions/{session_id}/agent/{TENANT_A_AGENT_ID}"
            f"?ticket={agent_ticket}&agent_token={AGENT_B_TOKEN}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert any(
                token in msg["message"].lower()
                for token in ("invalid", "credential", "mismatch", "tenant", "quarantine", "revok")
            )

        with client.websocket_connect(
            f"/remote-access/sessions/{session_id}/dashboard?ticket={dashboard_ticket}"
        ) as dashboard_ws:
            assert dashboard_ws.receive_json()["type"] == "session_state"
            with client.websocket_connect(
                f"/remote-access/sessions/{session_id}/agent/{TENANT_A_AGENT_ID}"
                f"?ticket={agent_ticket}&agent_token={AGENT_A_TOKEN}"
            ) as agent_ws:
                attached = agent_ws.receive_json()
                assert attached["type"] == "session_attached"
                assert attached["session"]["agent_credential_bound"] is True
    finally:
        _reset_sessions()


def test_parallel_tenant_sessions_do_not_cross_relay() -> None:
    """Two concurrent interactive sessions stay isolated on the wire."""
    client, user_a, user_b, _tenant_a, _tenant_b = _build_two_tenant_client()
    try:
        _as_user(client, user_a)
        payload_a = _queue_desktop(client, TENANT_A_AGENT_ID)
        session_a = payload_a["session_id"]
        dash_a = payload_a["dashboard_ticket"]
        agent_a = payload_a["agent_ticket"]

        _as_user(client, user_b)
        payload_b = _queue_desktop(client, TENANT_B_AGENT_ID)
        session_b = payload_b["session_id"]
        dash_b = payload_b["dashboard_ticket"]
        agent_b = payload_b["agent_ticket"]

        assert session_a != session_b
        assert len({dash_a, agent_a, dash_b, agent_b}) == 4

        # Exercise tenant A end-to-end, then tenant B, asserting foreign session_id drops.
        with client.websocket_connect(
            f"/remote-access/sessions/{session_a}/dashboard?ticket={dash_a}"
        ) as dash_ws_a:
            assert dash_ws_a.receive_json()["type"] == "session_state"
            with client.websocket_connect(
                f"/remote-access/sessions/{session_a}/agent/{TENANT_A_AGENT_ID}"
                f"?ticket={agent_a}&agent_token={AGENT_A_TOKEN}"
            ) as agent_ws_a:
                assert agent_ws_a.receive_json()["type"] == "session_attached"
                assert dash_ws_a.receive_json()["type"] == "agent_connected"

                agent_ws_a.send_json(
                    {"type": "output", "session_id": session_b, "data": "leaked-from-a"}
                )
                agent_ws_a.send_json(
                    {"type": "output", "session_id": session_a, "data": "ok-a"}
                )
                out_a = dash_ws_a.receive_json()
                assert out_a["type"] == "output"
                assert out_a["data"] == "ok-a"

        with client.websocket_connect(
            f"/remote-access/sessions/{session_b}/dashboard?ticket={dash_b}"
        ) as dash_ws_b:
            assert dash_ws_b.receive_json()["type"] == "session_state"
            with client.websocket_connect(
                f"/remote-access/sessions/{session_b}/agent/{TENANT_B_AGENT_ID}"
                f"?ticket={agent_b}&agent_token={AGENT_B_TOKEN}"
            ) as agent_ws_b:
                assert agent_ws_b.receive_json()["type"] == "session_attached"
                assert dash_ws_b.receive_json()["type"] == "agent_connected"

                agent_ws_b.send_json(
                    {"type": "output", "session_id": session_a, "data": "leaked-from-b"}
                )
                agent_ws_b.send_json(
                    {"type": "output", "session_id": session_b, "data": "ok-b"}
                )
                out_b = dash_ws_b.receive_json()
                assert out_b["type"] == "output"
                assert out_b["data"] == "ok-b"
    finally:
        _reset_sessions()


def test_worker_restart_rejects_stale_session_tickets() -> None:
    """In-memory session manager loss (worker restart) must fail closed."""
    client, user_a, _user_b, _tenant_a, _tenant_b = _build_two_tenant_client()
    try:
        _as_user(client, user_a)
        payload = _queue_desktop(client, TENANT_A_AGENT_ID)
        session_id = payload["session_id"]
        dashboard_ticket = payload["dashboard_ticket"]
        agent_ticket = payload["agent_ticket"]

        remote_session_manager._sessions.clear()

        assert remote_session_manager.get_session(session_id) is None

        with client.websocket_connect(
            f"/remote-access/sessions/{session_id}/dashboard?ticket={dashboard_ticket}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert any(
                token in msg["message"].lower()
                for token in ("not found", "expired", "different", "instance", "start remote")
            )

        with client.websocket_connect(
            f"/remote-access/sessions/{session_id}/agent/{TENANT_A_AGENT_ID}"
            f"?ticket={agent_ticket}&agent_token={AGENT_A_TOKEN}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"

        missing = client.get(f"/remote-access/sessions/{session_id}")
        assert missing.status_code == 404
    finally:
        _reset_sessions()
