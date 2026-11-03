from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Index, Text, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RemoteSessionRecord(Base):
    """Durable remote interactive session + purpose-scoped tickets.

    WebSocket connections are process-local and are not stored here.
    After a worker restart the record is rehydrated so clients can reconnect
    with still-valid tickets; agent_credential_bound resets to False until
    the agent re-authenticates.
    """

    __tablename__ = "remote_sessions"
    __table_args__ = (
        Index("ix_remote_sessions_tenant_id", "tenant_id"),
        Index("ix_remote_sessions_agent_id", "agent_id"),
        Index("ix_remote_sessions_status", "status"),
    )

    session_id: Mapped[str] = mapped_column(Text, primary_key=True)

    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_user_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    session_type: Mapped[str] = mapped_column(Text, nullable=False)
    command_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )

    # Ticket payloads: {token, purpose, expires_at, revoked, bound_at}
    dashboard_ticket: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    input_ticket: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    agent_ticket: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Bounded transcript for reconnect buffer (not a full audit log).
    transcript: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<RemoteSessionRecord(session_id={self.session_id}, "
            f"status={self.status}, agent_id={self.agent_id})>"
        )
