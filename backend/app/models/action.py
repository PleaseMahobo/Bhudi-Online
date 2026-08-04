from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy import JSON
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .device import Device
    from .tenant import Tenant


class Action(Base):
    __tablename__ = "actions"

    __table_args__ = (
        Index("idx_actions_device", "device_id"),
        Index("idx_actions_tenant", "tenant_id"),
        Index("idx_actions_status", "status"),
        Index("idx_actions_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    device_id: Mapped[uuid.UUID | None] = mapped_column(
        String(36),
        ForeignKey(
            "devices.id",
            ondelete="CASCADE",
        ),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        String(36),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=True,
    )

    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
    )

    result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    #
    # Relationships
    #

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="actions",
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="actions",
    )

    def __repr__(self) -> str:
        return (
            f"<Action("
            f"id={self.id}, "
            f"type={self.type!r}, "
            f"status={self.status!r}"
            f")>"
        )