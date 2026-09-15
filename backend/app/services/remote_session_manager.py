from __future__ import annotations

import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import WebSocket


_INPUT_EVENT_TYPES = frozenset(
    {
        "mouse",
        "mousemove",
        "mousedown",
        "mouseup",
        "click",
        "wheel",
        "keydown",
        "keyup",
        "keypress",
        "keyboard",
    }
)


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


@dataclass
class RemoteSessionState:
    session_id: str
    agent_id: str
    session_type: str
    command_id: str | None = None
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    input_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    dashboard_connections: list[WebSocket] = field(default_factory=list)
    agent_connection: WebSocket | None = None
    dashboard_input_connections: list[WebSocket] = field(default_factory=list)
    agent_input_connection: WebSocket | None = None
    transcript: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=200))
    pending_dashboard_messages: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    pending_input_messages: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))

    def snapshot(self, *, include_input_token: bool = False) -> dict[str, Any]:
        snapshot = {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "session_type": self.session_type,
            "command_id": self.command_id,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "agent_connected": self.agent_connection is not None,
            "dashboard_count": len(self.dashboard_connections),
            "input_channel_connected": self.agent_input_connection is not None,
            "transcript_length": len(self.transcript),
        }
        if include_input_token:
            snapshot["input_token"] = self.input_token
        return snapshot

    def valid_input_token(self, token: str | None) -> bool:
        return bool(token) and secrets.compare_digest(str(token), self.input_token)


class RemoteSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, RemoteSessionState] = {}

    def new_session_id(self) -> str:
        return str(uuid4())

    def create_session(
        self,
        *,
        agent_id: UUID | str,
        session_type: str,
        metadata: dict[str, Any] | None = None,
        command_id: UUID | str | None = None,
        session_id: UUID | str | None = None,
    ) -> RemoteSessionState:
        resolved_session_id = str(session_id or self.new_session_id())
        state = RemoteSessionState(
            session_id=resolved_session_id,
            agent_id=str(agent_id),
            session_type=session_type,
            command_id=str(command_id) if command_id is not None else None,
            metadata=metadata or {},
        )
        self._sessions[resolved_session_id] = state
        return state

    def get_session(self, session_id: UUID | str) -> RemoteSessionState | None:
        return self._sessions.get(str(session_id))

    def get_input_token(self, session_id: UUID | str) -> str | None:
        state = self.get_session(session_id)
        return state.input_token if state is not None else None

    def attach_command(self, session_id: UUID | str, command_id: UUID | str) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        if state is None:
            return None
        state.command_id = str(command_id)
        return state

    async def connect_dashboard(self, session_id: UUID | str, websocket: WebSocket) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        await websocket.accept()
        if state is None:
            print(f"[remote-session] dashboard connect: unknown session_id={session_id}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": "Session not found (expired, or different API instance). Start remote again.",
                })
            except Exception:
                pass
            await websocket.close(code=1008)
            return None

        if websocket.query_params.get("channel") == "input":
            token = websocket.query_params.get("token")
            if not state.valid_input_token(token):
                await websocket.send_json({"type": "error", "message": "Invalid remote input credentials."})
                await websocket.close(code=1008)
                return None
            state.dashboard_input_connections.append(websocket)
            await websocket.send_json({
                "type": "input_channel_ready",
                "session_id": state.session_id,
                "authenticated_at_ms": _now_ms(),
            })
            return state

        state.dashboard_connections.append(websocket)
        await websocket.send_json({
            "type": "session_state",
            "session": state.snapshot(),
            "buffer": list(state.transcript),
        })
        return state

    async def connect_agent(self, session_id: UUID | str, agent_id: UUID | str, websocket: WebSocket) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        await websocket.accept()
        if state is None or state.agent_id != str(agent_id):
            print(
                f"[remote-session] agent connect rejected session={session_id} "
                f"agent={agent_id} known={state.agent_id if state else None}"
            )
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": "Session not found or agent mismatch. Re-enroll agent and retry.",
                })
            except Exception:
                pass
            await websocket.close(code=1008)
            return None

        if websocket.query_params.get("channel") == "input":
            token = websocket.query_params.get("token")
            if not state.valid_input_token(token):
                await websocket.send_json({"type": "error", "message": "Invalid remote input credentials."})
                await websocket.close(code=1008)
                return None
            if state.agent_input_connection is not None:
                try:
                    await state.agent_input_connection.close(code=1012)
                except Exception:
                    pass
            state.agent_input_connection = websocket
            await websocket.send_json({
                "type": "input_channel_ready",
                "session": state.snapshot(),
                "authenticated_at_ms": _now_ms(),
            })
            while state.pending_input_messages:
                await websocket.send_json(state.pending_input_messages.popleft())
            return state

        if state.agent_connection is not None:
            try:
                await state.agent_connection.close(code=1012)
            except Exception:
                pass
        state.agent_connection = websocket
        state.status = "active"
        await websocket.send_json({"type": "session_attached", "session": state.snapshot()})
        await self._broadcast_to_dashboards(state, {"type": "agent_connected", "session": state.snapshot()})

        while state.pending_dashboard_messages:
            await websocket.send_json(state.pending_dashboard_messages.popleft())

        return state

    async def disconnect_dashboard(self, session_id: UUID | str, websocket: WebSocket) -> None:
        state = self.get_session(session_id)
        if state is None:
            return
        was_input = websocket in state.dashboard_input_connections
        if was_input:
            state.dashboard_input_connections.remove(websocket)
        if websocket in state.dashboard_connections:
            state.dashboard_connections.remove(websocket)
        if not was_input and not state.dashboard_connections and state.agent_connection is None:
            state.status = "idle"

    async def disconnect_agent(self, session_id: UUID | str, websocket: WebSocket | None = None) -> None:
        state = self.get_session(session_id)
        if state is None:
            return
        was_input = websocket is not None and state.agent_input_connection is websocket
        if websocket is None or state.agent_input_connection is websocket:
            state.agent_input_connection = None
        was_video = websocket is None or state.agent_connection is websocket
        if was_video:
            state.agent_connection = None
        if was_input and not was_video:
            return
        if state.status != "closed":
            state.status = "waiting_for_agent"
        await self._broadcast_to_dashboards(state, {"type": "agent_disconnected", "session": state.snapshot()})

    async def relay_dashboard_message(self, session_id: UUID | str, message: dict[str, Any]) -> None:
        state = self.get_session(session_id)
        if state is None:
            return

        if message.get("type") in _INPUT_EVENT_TYPES:
            enriched = dict(message)
            enriched["backend_received_at_ms"] = _now_ms()
            envelope = {"type": "input", "payload": enriched}
            if state.agent_input_connection is None:
                state.pending_input_messages.append(envelope)
                return
            await state.agent_input_connection.send_json(envelope)
            return

        envelope = {"type": "dashboard_message", "payload": message}
        if message.get("type") == "close":
            state.status = "closed"

        if state.agent_connection is None:
            state.pending_dashboard_messages.append(envelope)
            return

        await state.agent_connection.send_json(envelope)

    async def relay_agent_message(self, session_id: UUID | str, message: dict[str, Any]) -> None:
        state = self.get_session(session_id)
        if state is None:
            return

        state.transcript.append(message)
        event_type = str(message.get("type") or "")
        if event_type in {"ready", "desktop_ready"}:
            state.status = "active"
        elif event_type == "session_closed":
            state.status = "closed"
        if event_type.startswith("input_") or event_type == "input_channel_ready":
            return
        await self._broadcast_to_dashboards(state, message)

    async def close_session(self, session_id: UUID | str, reason: str = "closed_by_operator") -> RemoteSessionState | None:
        state = self.get_session(session_id)
        if state is None:
            return None
        state.status = "closed"
        message = {"type": "close", "reason": reason, "session_id": state.session_id}
        if state.agent_connection is not None:
            await state.agent_connection.send_json(message)
        if state.agent_input_connection is not None:
            try:
                await state.agent_input_connection.send_json(message)
            except Exception:
                pass
        await self._broadcast_to_dashboards(state, {"type": "session_closed", "reason": reason, "session": state.snapshot()})
        for websocket in state.dashboard_input_connections:
            try:
                await websocket.send_json({"type": "session_closed", "reason": reason, "session": state.snapshot()})
            except Exception:
                pass
        return state

    async def _broadcast_to_dashboards(self, state: RemoteSessionState, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for websocket in state.dashboard_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            if websocket in state.dashboard_connections:
                state.dashboard_connections.remove(websocket)


remote_session_manager = RemoteSessionManager()
