from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CommandStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class CommandPriority(int, Enum):
    LOW = 10
    NORMAL = 50
    HIGH = 90
    CRITICAL = 100


class AgentCommand(Base):
    __tablename__ = "agent_commands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    issued_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    command_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=CommandStatus.PENDING.value,
        index=True,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=str(CommandPriority.NORMAL.value),
        index=True,
    )

    queued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="300",
    )

    result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    stdout: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    stderr: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    exit_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="3",
    )

    acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    requires_reboot: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    checksum: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    agent = relationship("Agent", back_populates="commands")
    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AgentCommand("
            f"id={self.id}, "
            f"type={self.command_type}, "
            f"status={self.status})>"
        )