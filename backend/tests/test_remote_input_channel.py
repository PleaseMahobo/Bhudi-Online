from __future__ import annotations

import uuid

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
from app.models.user import User


TEST_AGENT_ID = "44444444-4444-4444-8444-44444444444d"


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

    db = session_factory()
    db.add(
        Agent(
            id=uuid.UUID(TEST_AGENT_ID),
            hostname="input-agent-01",
            platform="windows",
            approved=True,
            enabled=True,
            command_timeout=300,
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
    test_user = User(id=uuid.uuid4(), email="input@example.com", active=True, mfa_enabled=True)
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_mfa_for_actions] = lambda: test_user
    return TestClient(app)


def test_authenticated_input_channel_is_separate_and_timestamped() -> None:
    client = _build_client()
    queued = client.post(
        "/remote-access/desktop",
        json={"agent_id": TEST_AGENT_ID, "session_mode": "control", "display_protocol": "native"},
    )
    assert queued.status_code == 201
    response = queued.json()
    session_id = response["session_id"]
    input_token = response["payload"]["input_token"]
    assert input_token

    with client.websocket_connect(f"/remote-access/sessions/{session_id}/dashboard") as dashboard_ws:
        dashboard_ws.receive_json()
        with client.websocket_connect(f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}") as agent_ws:
            agent_ws.receive_json()
            dashboard_ws.receive_json()

            with client.websocket_connect(
                f"/remote-access/sessions/{session_id}/dashboard?channel=input&token={input_token}"
            ) as input_dashboard_ws:
                assert input_dashboard_ws.receive_json()["type"] == "input_channel_ready"
                with client.websocket_connect(
                    f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}?channel=input&token={input_token}"
                ) as input_agent_ws:
                    assert input_agent_ws.receive_json()["type"] == "input_channel_ready"

                    input_dashboard_ws.send_json(
                        {
                            "type": "mousedown",
                            "event_id": "input-test-1",
                            "browser_sent_at_ms": 1000,
                            "x": 0.25,
                            "y": 0.5,
                        }
                    )
                    forwarded = input_agent_ws.receive_json()
                    assert forwarded["type"] == "input"
                    payload = forwarded["payload"]
                    assert payload["type"] == "mousedown"
                    assert payload["event_id"] == "input-test-1"
                    assert payload["browser_sent_at_ms"] == 1000
                    assert isinstance(payload["backend_received_at_ms"], int)

                    input_agent_ws.send_json(
                        {
                            "type": "input_ack",
                            "session_id": session_id,
                            "event_id": "input-test-1",
                            "browser_sent_at_ms": 1000,
                            "backend_received_at_ms": payload["backend_received_at_ms"],
                            "agent_received_at_ms": 1010,
                            "windows_input_at_ms": 1011,
                            "ack_sent_at_ms": 1012,
                        }
                    )
                    ack = input_dashboard_ws.receive_json()
                    assert ack["type"] == "input_ack"
                    assert ack["event_id"] == "input-test-1"
                    assert ack["windows_input_at_ms"] == 1011


def test_input_channel_rejects_invalid_session_credential() -> None:
    client = _build_client()
    queued = client.post(
        "/remote-access/desktop",
        json={"agent_id": TEST_AGENT_ID, "session_mode": "control", "display_protocol": "native"},
    )
    session_id = queued.json()["session_id"]

    with client.websocket_connect(
        f"/remote-access/sessions/{session_id}/dashboard?channel=input&token=not-the-session-token"
    ) as ws:
        assert ws.receive_json()["type"] == "error"
