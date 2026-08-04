from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import remote_access
from app.core import bootstrap
from app.database.session import get_db
from app.models.agent import Agent


TEST_AGENT_ID = "33333333-3333-4333-8333-33333333333c"


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
            hostname="stream-agent-01",
            platform="windows",
            approved=True,
            enabled=True,
            command_timeout=300,
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
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_terminal_session_relays_dashboard_input_and_agent_output() -> None:
    client = _build_client()
    queue_response = client.post(
        "/remote-access/terminal",
        json={
            "agent_id": TEST_AGENT_ID,
            "shell": "powershell",
            "interactive": True,
        },
    )
    assert queue_response.status_code == 201
    payload = queue_response.json()
    session_id = payload["session_id"]

    with client.websocket_connect(f"/remote-access/sessions/{session_id}/dashboard") as dashboard_ws:
        initial = dashboard_ws.receive_json()
        assert initial["type"] == "session_state"

        with client.websocket_connect(f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}") as agent_ws:
            attached = agent_ws.receive_json()
            assert attached["type"] == "session_attached"

            connected = dashboard_ws.receive_json()
            assert connected["type"] == "agent_connected"

            dashboard_ws.send_json({"type": "input", "data": "whoami\n"})
            agent_message = agent_ws.receive_json()
            assert agent_message["type"] == "dashboard_message"
            assert agent_message["payload"]["type"] == "input"
            assert agent_message["payload"]["data"] == "whoami\n"

            agent_ws.send_json({"type": "output", "session_id": session_id, "data": "bhudi\\operator"})
            output = dashboard_ws.receive_json()
            assert output["type"] == "output"
            assert output["data"] == "bhudi\\operator"

    session_response = client.get(f"/remote-access/sessions/{session_id}")
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["session_type"] == "terminal"
    assert session_payload["transcript_length"] >= 1


def test_desktop_session_relays_control_events_and_close() -> None:
    client = _build_client()
    queue_response = client.post(
        "/remote-access/desktop",
        json={
            "agent_id": TEST_AGENT_ID,
            "session_mode": "control",
            "display_protocol": "rdp",
        },
    )
    assert queue_response.status_code == 201
    payload = queue_response.json()
    session_id = payload["session_id"]

    with client.websocket_connect(f"/remote-access/sessions/{session_id}/dashboard") as dashboard_ws:
        dashboard_ws.receive_json()
        with client.websocket_connect(f"/remote-access/sessions/{session_id}/agent/{TEST_AGENT_ID}") as agent_ws:
            agent_ws.receive_json()
            dashboard_ws.receive_json()

            dashboard_ws.send_json({"type": "pointer", "x": 100, "y": 50, "buttons": 1})
            control_message = agent_ws.receive_json()
            assert control_message["type"] == "dashboard_message"
            assert control_message["payload"]["type"] == "pointer"

            agent_ws.send_json({"type": "desktop_event_ack", "session_id": session_id, "event": "pointer", "payload": {"x": 100, "y": 50}})
            acknowledged = dashboard_ws.receive_json()
            assert acknowledged["type"] == "desktop_event_ack"
            assert acknowledged["event"] == "pointer"

    close_response = client.post(f"/remote-access/sessions/{session_id}/close")
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"