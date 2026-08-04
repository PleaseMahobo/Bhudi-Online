from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.user import User


# ==========================================================
# Command Types
# ==========================================================


class CommandType(str, enum.Enum):

    POWERSHELL = "powershell"

    BASH = "bash"

    CMD = "cmd"

    PYTHON = "python"

    REBOOT = "reboot"

    SHUTDOWN = "shutdown"

    LOGOFF = "logoff"

    FILE_UPLOAD = "file_upload"

    FILE_DOWNLOAD = "file_download"

    PATCH_SCAN = "patch_scan"

    PATCH_INSTALL = "patch_install"

    SOFTWARE_INSTALL = "software_install"

    SOFTWARE_UNINSTALL = "software_uninstall"

    INVENTORY_REFRESH = "inventory_refresh"

    PROCESS_LIST = "process_list"

    SERVICE_LIST = "service_list"

    EVENT_LOG = "event_log"

    REGISTRY = "registry"

    CUSTOM = "custom"


# ==========================================================
# Status
# ==========================================================


class CommandStatus(str, enum.Enum):

    QUEUED = "queued"

    SENT = "sent"

    RUNNING = "running"

    SUCCESS = "success"

    FAILED = "failed"

    CANCELLED = "cancelled"

    TIMED_OUT = "timed_out"


# ==========================================================
# Command
# ==========================================================


class Command(Base):

    __tablename__ = "commands"

    __table_args__ = (

        Index("ix_command_agent_status", "agent_id", "status"),

        Index("ix_command_created", "created_at"),

    )

    #
    # Identity
    #

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    #
    # Relationships
    #

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "agents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
    )

    #
    # Command
    #

    command_type: Mapped[CommandType] = mapped_column(
        Enum(CommandType),
        nullable=False,
    )

    command_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    arguments: Mapped[str | None] = mapped_column(
        Text,
    )

    working_directory: Mapped[str | None] = mapped_column(
        Text,
    )

    run_as_system: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
    )

    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        server_default="300",
        nullable=False,
    )

    #
    # Execution
    #

    status: Mapped[CommandStatus] = mapped_column(
        Enum(CommandStatus),
        nullable=False,
        server_default="queued",
    )

    stdout: Mapped[str | None] = mapped_column(
        Text,
    )

    stderr: Mapped[str | None] = mapped_column(
        Text,
    )

    exit_code: Mapped[int | None] = mapped_column(
        Integer,
    )

    #
    # Timing
    #

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    #
    # Relationships
    #

    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="commands",
    )

    creator: Mapped["User | None"] = relationship(
        "User",
    )

    #
    # Representation
    #

    def __repr__(self) -> str:

        return (
            f"<Command("
            f"{self.id}, "
            f"{self.command_type.value}, "
            f"{self.status.value}"
            f")>"
        )