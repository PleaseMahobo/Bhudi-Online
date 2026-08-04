from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text, func
from sqlalchemy.types import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .device import Device
    from .incident import Incident
    from .tenant import Tenant


class ResponseAction(Base):
    __tablename__ = "response_actions"

    __table_args__ = (
        Index("idx_response_actions_incident", "incident_id"),
        Index("idx_response_actions_device", "device_id"),
        Index("idx_response_actions_tenant", "tenant_id"),
        Index("idx_response_actions_status", "status"),
        Index("idx_response_actions_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey(
            "incidents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
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

    action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
    )

    initiated_by: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    #
    # Relationships
    #

    incident: Mapped["Incident"] = relationship(
        "Incident",
        back_populates="response_actions",
    )

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="response_actions",
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="response_actions",
    )

    def __repr__(self) -> str:
        return (
            f"<ResponseAction("
            f"id={self.id}, "
            f"action={self.action!r}, "
            f"status={self.status!r}"
            f")>"
        )