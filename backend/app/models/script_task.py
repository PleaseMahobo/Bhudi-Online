from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .device import Device
    from .script import Script
    from .tenant import Tenant


class ScriptTask(Base):
    __tablename__ = "script_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False,
    )

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'pending'"),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    exit_code: Mapped[int | None] = mapped_column()

    output: Mapped[str | None] = mapped_column(
        Text,
    )

    error_output: Mapped[str | None] = mapped_column(
        Text,
    )

    parameters: Mapped[dict | None] = mapped_column(
        JSONB,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    #
    # Relationships
    #

    script: Mapped["Script"] = relationship(
        "Script",
        back_populates="tasks",
    )

    device: Mapped["Device"] = relationship(
        "Device",
        back_populates="script_tasks",
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="script_tasks",
    )

    def __repr__(self) -> str:
        return (
            f"<ScriptTask("
            f"id={self.id}, "
            f"status={self.status!r}"
            f")>"
        )