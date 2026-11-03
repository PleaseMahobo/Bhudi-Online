from __future__ import annotations

import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import WebSocket


TicketPurpose = Literal["dashboard", "input", "agent"]

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

DEFAULT_TICKET_TTL_SECONDS = 15 * 60


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _new_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass
class SessionTicket:
    """Short-lived, purpose-scoped credential for a remote session channel."""

    token: str
    purpose: TicketPurpose
    expires_at: float
    revoked: bool = False
    bound_at: float | None = None

    def is_valid(self, *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        if self.revoked:
            return False
        if current > self.expires_at:
            return False
        return True

    def bind(self) -> None:
        if self.bound_at is None:
            self.bound_at = time.time()

    def revoke(self) -> None:
        self.revoked = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "purpose": self.purpose,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "bound_at": self.bound_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SessionTicket | None:
        if not data or not isinstance(data, dict):
            return None
        token = data.get("token")
        purpose = data.get("purpose")
        expires_at = data.get("expires_at")
        if not token or purpose not in ("dashboard", "input", "agent") or expires_at is None:
            return None
        try:
            return cls(
                token=str(token),
                purpose=purpose,  # type: ignore[arg-type]
                expires_at=float(expires_at),
                revoked=bool(data.get("revoked", False)),
                bound_at=float(data["bound_at"]) if data.get("bound_at") is not None else None,
            )
        except (TypeError, ValueError):
            return None


@dataclass
class RemoteSessionState:
    session_id: str
    agent_id: str
    tenant_id: str
    owner_user_id: str
    session_type: str
    command_id: str | None = None
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dashboard_ticket: SessionTicket | None = None
    input_ticket: SessionTicket | None = None
    agent_ticket: SessionTicket | None = None
    # Process-local only — never persisted.
    dashboard_connections: list[WebSocket] = field(default_factory=list)
    agent_connection: WebSocket | None = None
    dashboard_input_connections: list[WebSocket] = field(default_factory=list)
    agent_input_connection: WebSocket | None = None
    agent_credential_bound: bool = False
    transcript: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=200))
    pending_dashboard_messages: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    pending_input_messages: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))

    @property
    def input_token(self) -> str:
        if self.input_ticket is None:
            return ""
        return self.input_ticket.token

    def snapshot(self, *, include_tickets: bool = False) -> dict[str, Any]:
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
            "agent_credential_bound": self.agent_credential_bound,
            "transcript_length": len(self.transcript),
        }
        if include_tickets:
            snapshot["dashboard_ticket"] = (
                self.dashboard_ticket.token if self.dashboard_ticket and self.dashboard_ticket.is_valid() else None
            )
            snapshot["input_ticket"] = (
                self.input_ticket.token if self.input_ticket and self.input_ticket.is_valid() else None
            )
            snapshot["agent_ticket"] = (
                self.agent_ticket.token if self.agent_ticket and self.agent_ticket.is_valid() else None
            )
            snapshot["input_token"] = snapshot["input_ticket"]
        return snapshot

    def valid_input_token(self, token: str | None) -> bool:
        return self.validate_ticket("input", token)

    def validate_ticket(self, purpose: TicketPurpose, token: str | None) -> bool:
        if not token:
            return False
        ticket = self._ticket_for(purpose)
        if ticket is None or not ticket.is_valid():
            return False
        return secrets.compare_digest(str(token), ticket.token)

    def _ticket_for(self, purpose: TicketPurpose) -> SessionTicket | None:
        if purpose == "dashboard":
            return self.dashboard_ticket
        if purpose == "input":
            return self.input_ticket
        if purpose == "agent":
            return self.agent_ticket
        return None

    def bind_ticket(self, purpose: TicketPurpose, token: str | None) -> bool:
        if not self.validate_ticket(purpose, token):
            return False
        ticket = self._ticket_for(purpose)
        if ticket is not None:
            ticket.bind()
        return True

    def revoke_tickets(self) -> None:
        for ticket in (self.dashboard_ticket, self.input_ticket, self.agent_ticket):
            if ticket is not None:
                ticket.revoke()


class RemoteSessionManager:
    def __init__(self, *, ticket_ttl_seconds: int = DEFAULT_TICKET_TTL_SECONDS) -> None:
        self._sessions: dict[str, RemoteSessionState] = {}
        self._ticket_ttl_seconds = ticket_ttl_seconds

    def new_session_id(self) -> str:
        return str(uuid4())

    def _issue_ticket(self, purpose: TicketPurpose, *, ttl_seconds: int | None = None) -> SessionTicket:
        ttl = self._ticket_ttl_seconds if ttl_seconds is None else ttl_seconds
        return SessionTicket(
            token=_new_token(),
            purpose=purpose,
            expires_at=time.time() + max(1, int(ttl)),
        )

    def _session_local(self):
        """Resolve SessionLocal dynamically so tests can patch it."""
        import app.database.session as db_session

        return db_session.SessionLocal()

    def _persist(self, state: RemoteSessionState) -> None:
        """Write durable session fields to the database (best-effort)."""
        try:
            from app.models.remote_session import RemoteSessionRecord

            db = self._session_local()
        except Exception as exc:
            print(f"[remote-session] persist skipped (no db): {exc}")
            return
        try:
            row = db.get(RemoteSessionRecord, state.session_id)
            if row is None:
                row = RemoteSessionRecord(session_id=state.session_id)
                db.add(row)
            row.agent_id = state.agent_id
            row.tenant_id = state.tenant_id
            row.owner_user_id = state.owner_user_id
            row.session_type = state.session_type
            row.command_id = state.command_id
            row.status = state.status
            row.metadata_json = dict(state.metadata or {})
            row.dashboard_ticket = state.dashboard_ticket.to_dict() if state.dashboard_ticket else None
            row.input_ticket = state.input_ticket.to_dict() if state.input_ticket else None
            row.agent_ticket = state.agent_ticket.to_dict() if state.agent_ticket else None
            row.transcript = list(state.transcript)
            row.created_at = state.created_at
            db.commit()
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[remote-session] persist failed session={state.session_id}: {exc}")
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _hydrate(self, session_id: str) -> RemoteSessionState | None:
        try:
            from app.models.remote_session import RemoteSessionRecord

            db = self._session_local()
        except Exception:
            return None
        try:
            row = db.get(RemoteSessionRecord, session_id)
            if row is None:
                return None
            state = RemoteSessionState(
                session_id=row.session_id,
                agent_id=row.agent_id,
                tenant_id=row.tenant_id or "",
                owner_user_id=row.owner_user_id or "",
                session_type=row.session_type,
                command_id=row.command_id,
                status=row.status or "pending",
                metadata=dict(row.metadata_json or {}),
                created_at=row.created_at or datetime.now(timezone.utc).isoformat(),
                dashboard_ticket=SessionTicket.from_dict(row.dashboard_ticket),
                input_ticket=SessionTicket.from_dict(row.input_ticket),
                agent_ticket=SessionTicket.from_dict(row.agent_ticket),
                # Connections and credential binding are process-local.
                agent_credential_bound=False,
            )
            if row.transcript:
                state.transcript.extend(row.transcript[-200:])
            self._sessions[session_id] = state
            return state
        except Exception as exc:
            print(f"[remote-session] hydrate failed session={session_id}: {exc}")
            return None
        finally:
            try:
                db.close()
            except Exception:
                pass

    def create_session(
        self,
        *,
        agent_id: UUID | str,
        session_type: str,
        tenant_id: UUID | str | None = None,
        owner_user_id: UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        command_id: UUID | str | None = None,
        session_id: UUID | str | None = None,
        ticket_ttl_seconds: int | None = None,
    ) -> RemoteSessionState:
        resolved_session_id = str(session_id or self.new_session_id())
        state = RemoteSessionState(
            session_id=resolved_session_id,
            agent_id=str(agent_id),
            tenant_id=str(tenant_id) if tenant_id is not None else "",
            owner_user_id=str(owner_user_id) if owner_user_id is not None else "",
            session_type=session_type,
            command_id=str(command_id) if command_id is not None else None,
            metadata=metadata or {},
            dashboard_ticket=self._issue_ticket("dashboard", ttl_seconds=ticket_ttl_seconds),
            input_ticket=self._issue_ticket("input", ttl_seconds=ticket_ttl_seconds),
            agent_ticket=self._issue_ticket("agent", ttl_seconds=ticket_ttl_seconds),
        )
        self._sessions[resolved_session_id] = state
        self._persist(state)
        return state

    def get_session(self, session_id: UUID | str) -> RemoteSessionState | None:
        key = str(session_id)
        state = self._sessions.get(key)
        if state is not None:
            return state
        return self._hydrate(key)

    def get_input_token(self, session_id: UUID | str) -> str | None:
        state = self.get_session(session_id)
        if state is None or state.input_ticket is None or not state.input_ticket.is_valid():
            return None
        return state.input_ticket.token

    def get_session_tickets(self, session_id: UUID | str) -> dict[str, str | None]:
        state = self.get_session(session_id)
        if state is None:
            return {"dashboard": None, "input": None, "agent": None, "input_token": None}
        snap = state.snapshot(include_tickets=True)
        return {
            "dashboard": snap.get("dashboard_ticket"),
            "input": snap.get("input_ticket"),
            "agent": snap.get("agent_ticket"),
            "input_token": snap.get("input_token"),
        }

    def reissue_tickets(
        self,
        session_id: UUID | str,
        *,
        ticket_ttl_seconds: int | None = None,
    ) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        if state is None:
            return None
        state.revoke_tickets()
        state.dashboard_ticket = self._issue_ticket("dashboard", ttl_seconds=ticket_ttl_seconds)
        state.input_ticket = self._issue_ticket("input", ttl_seconds=ticket_ttl_seconds)
        state.agent_ticket = self._issue_ticket("agent", ttl_seconds=ticket_ttl_seconds)
        self._persist(state)
        return state

    def revoke_session_tickets(self, session_id: UUID | str) -> bool:
        state = self.get_session(session_id)
        if state is None:
            return False
        state.revoke_tickets()
        self._persist(state)
        return True

    def attach_command(self, session_id: UUID | str, command_id: UUID | str) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        if state is None:
            return None
        state.command_id = str(command_id)
        self._persist(state)
        return state

    def _extract_ticket(self, websocket: WebSocket) -> str | None:
        params = websocket.query_params
        return params.get("ticket") or params.get("token")

    async def _reject(self, websocket: WebSocket, message: str) -> None:
        try:
            await websocket.send_json({"type": "error", "message": message})
        except Exception:
            pass
        try:
            await websocket.close(code=1008)
        except Exception:
            pass

    async def connect_dashboard(self, session_id: UUID | str, websocket: WebSocket) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        await websocket.accept()
        if state is None:
            print(f"[remote-session] dashboard connect: unknown session_id={session_id}")
            await self._reject(
                websocket,
                "Session not found (expired, or different API instance). Start remote again.",
            )
            return None

        if state.status == "closed":
            await self._reject(websocket, "Session is closed.")
            return None

        ticket_value = self._extract_ticket(websocket)
        is_input = websocket.query_params.get("channel") == "input"
        purpose: TicketPurpose = "input" if is_input else "dashboard"

        if not state.bind_ticket(purpose, ticket_value):
            await self._reject(websocket, "Invalid or expired remote session ticket.")
            return None

        self._persist(state)

        if is_input:
            state.dashboard_input_connections.append(websocket)
            await websocket.send_json(
                {
                    "type": "input_channel_ready",
                    "session_id": state.session_id,
                    "authenticated_at_ms": _now_ms(),
                }
            )
            return state

        state.dashboard_connections.append(websocket)
        await websocket.send_json(
            {
                "type": "session_state",
                "session": state.snapshot(),
                "buffer": list(state.transcript),
            }
        )
        return state

    async def connect_agent(
        self,
        session_id: UUID | str,
        agent_id: UUID | str,
        websocket: WebSocket,
        *,
        agent_credential_verified: bool = False,
    ) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        await websocket.accept()
        if state is None or state.agent_id != str(agent_id):
            print(
                f"[remote-session] agent connect rejected session={session_id} "
                f"agent={agent_id} known={state.agent_id if state else None}"
            )
            await self._reject(websocket, "Session not found or agent mismatch. Re-enroll agent and retry.")
            return None

        if state.status == "closed":
            await self._reject(websocket, "Session is closed.")
            return None

        if not agent_credential_verified:
            await self._reject(websocket, "Agent credentials required.")
            return None

        ticket_value = self._extract_ticket(websocket)
        is_input = websocket.query_params.get("channel") == "input"
        if is_input:
            ok = state.bind_ticket("input", ticket_value) or state.bind_ticket("agent", ticket_value)
        else:
            ok = state.bind_ticket("agent", ticket_value)

        if not ok:
            await self._reject(websocket, "Invalid or expired remote session ticket.")
            return None

        state.agent_credential_bound = True

        if is_input:
            if state.agent_input_connection is not None:
                try:
                    await state.agent_input_connection.close(code=1012)
                except Exception:
                    pass
            state.agent_input_connection = websocket
            self._persist(state)
            await websocket.send_json(
                {
                    "type": "input_channel_ready",
                    "session": state.snapshot(),
                    "authenticated_at_ms": _now_ms(),
                }
            )
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
        self._persist(state)
        await websocket.send_json({"type": "session_attached", "session": state.snapshot()})
        await self._broadcast_to_dashboards(
            state, {"type": "agent_connected", "session": state.snapshot()}
        )

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
            self._persist(state)

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
        if state.agent_connection is None and state.agent_input_connection is None:
            state.agent_credential_bound = False
        if was_input and not was_video:
            return
        if state.status != "closed":
            state.status = "waiting_for_agent"
        self._persist(state)
        await self._broadcast_to_dashboards(
            state, {"type": "agent_disconnected", "session": state.snapshot()}
        )

    def _message_bound_to_session(self, state: RemoteSessionState, message: dict[str, Any]) -> bool:
        """Reject cross-session injection when a message carries a session_id."""
        claimed = message.get("session_id")
        if claimed is None:
            return True
        return str(claimed) == state.session_id

    async def relay_dashboard_input_message(
        self,
        session_id: UUID | str,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> bool:
        state = self.get_session(session_id)
        if state is None or websocket not in state.dashboard_input_connections:
            return False
        if state.input_ticket is None or not state.input_ticket.is_valid():
            return False
        if not self._message_bound_to_session(state, message):
            return False
        if message.get("type") not in _INPUT_EVENT_TYPES:
            return False
        enriched = dict(message)
        enriched["backend_received_at_ms"] = _now_ms()
        envelope = {"type": "input", "payload": enriched}
        if state.agent_input_connection is None:
            state.pending_input_messages.append(envelope)
        else:
            await state.agent_input_connection.send_json(envelope)
        return True

    async def relay_dashboard_message(self, session_id: UUID | str, message: dict[str, Any]) -> None:
        state = self.get_session(session_id)
        if state is None:
            return

        if message.get("type") in _INPUT_EVENT_TYPES:
            return
        if not self._message_bound_to_session(state, message):
            return

        envelope = {"type": "dashboard_message", "payload": message}
        if message.get("type") == "close":
            state.status = "closed"
            state.revoke_tickets()
            self._persist(state)

        if state.agent_connection is None:
            state.pending_dashboard_messages.append(envelope)
            return

        await state.agent_connection.send_json(envelope)

    async def relay_agent_input_message(
        self,
        session_id: UUID | str,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> bool:
        state = self.get_session(session_id)
        if state is None or state.agent_input_connection is not websocket:
            return False
        if not state.agent_credential_bound:
            return False
        if not self._message_bound_to_session(state, message):
            return False
        for dashboard in list(state.dashboard_input_connections):
            try:
                await dashboard.send_json(message)
            except Exception:
                if dashboard in state.dashboard_input_connections:
                    state.dashboard_input_connections.remove(dashboard)
        return True

    async def relay_agent_message(self, session_id: UUID | str, message: dict[str, Any]) -> None:
        state = self.get_session(session_id)
        if state is None:
            return
        if not state.agent_credential_bound:
            return
        if not self._message_bound_to_session(state, message):
            return

        state.transcript.append(message)
        event_type = str(message.get("type") or "")
        if event_type in {"ready", "desktop_ready"}:
            state.status = "active"
            self._persist(state)
        elif event_type == "session_closed":
            state.status = "closed"
            state.revoke_tickets()
            self._persist(state)
        if event_type.startswith("input_") or event_type == "input_channel_ready":
            return
        await self._broadcast_to_dashboards(state, message)

    async def close_session(
        self, session_id: UUID | str, reason: str = "closed_by_operator"
    ) -> RemoteSessionState | None:
        state = self.get_session(session_id)
        if state is None:
            return None
        state.status = "closed"
        state.revoke_tickets()
        self._persist(state)
        message = {"type": "close", "reason": reason, "session_id": state.session_id}
        if state.agent_connection is not None:
            try:
                await state.agent_connection.send_json(message)
            except Exception:
                pass
        if state.agent_input_connection is not None:
            try:
                await state.agent_input_connection.send_json(message)
            except Exception:
                pass
        await self._broadcast_to_dashboards(
            state, {"type": "session_closed", "reason": reason, "session": state.snapshot()}
        )
        for websocket in list(state.dashboard_input_connections):
            try:
                await websocket.send_json(
                    {"type": "session_closed", "reason": reason, "session": state.snapshot()}
                )
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
