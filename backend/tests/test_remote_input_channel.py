from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

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
from app.services.remote_session_manager import RemoteSessionManager


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


class _FakeWebSocket:
    def __init__(self, query_params: dict[str, str] | None = None) -> None:
        self.query_params = query_params or {}
        self.sent: list[dict] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)

    async def close(self, code: int = 1000) -> None:
        pass


def test_authenticated_input_channel_is_separate_and_timestamped() -> None:
    async def exercise() -> None:
        manager = RemoteSessionManager()
        session = manager.create_session(
            agent_id=TEST_AGENT_ID,
            session_type="desktop",
            metadata={"session_mode": "control"},
        )
        token = session.input_token

        dashboard = _FakeWebSocket({"channel": "input", "token": token})
        agent = _FakeWebSocket({"channel": "input", "token": token})
        assert await manager.connect_dashboard(session.session_id, dashboard) is session
        assert await manager.connect_agent(session.session_id, TEST_AGENT_ID, agent) is session
        assert dashboard.sent[0]["type"] == "input_channel_ready"
        assert agent.sent[0]["type"] == "input_channel_ready"

        await manager.relay_dashboard_message(
            session.session_id,
            {
                "type": "input",
                "payload": {
                    "type": "mousedown",
                    "event_id": "input-test-1",
                    "browser_sent_at_ms": 1000,
                    "x": 0.25,
                    "y": 0.5,
                },
            },
        )
        forwarded = agent.sent[-1]
        assert forwarded["type"] == "input"
        payload = forwarded["payload"]
        assert payload["type"] == "mousedown"
        assert payload["event_id"] == "input-test-1"
        assert payload["browser_sent_at_ms"] == 1000
        assert isinstance(payload["backend_received_at_ms"], int)

        await manager.relay_agent_message(
            session.session_id,
            {
                "type": "input_ack",
                "session_id": session.session_id,
                "event_id": "input-test-1",
                "browser_sent_at_ms": 1000,
                "backend_received_at_ms": payload["backend_received_at_ms"],
                "agent_received_at_ms": 1010,
                "windows_input_at_ms": 1011,
                "ack_sent_at_ms": 1012,
            },
        )
        # Input acknowledgements are deliberately not broadcast on the video channel.
        assert all(message.get("type") != "input_ack" for message in dashboard.sent)

    asyncio.run(exercise())


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
