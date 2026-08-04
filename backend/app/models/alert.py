from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .device import Device
    from .tenant import Tenant


class Alert(Base):
    __tablename__ = "alerts"

    __table_args__ = (
        Index("idx_alerts_device", "device_id"),
        Index("idx_alerts_tenant", "tenant_id"),
        Index("idx_alerts_severity", "severity"),
        Index("idx_alerts_type", "type"),
        Index("idx_alerts_resolved", "resolved"),
        Index("idx_alerts_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "devices.id",
            ondelete="CASCADE",
        ),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
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

    severity: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    threat_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    mitre_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    mitre_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
    )

    #
    # Relationships
    #

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="alerts",
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="alerts",
    )

    def __repr__(self) -> str:
        return (
            f"<Alert("
            f"id={self.id}, "
            f"severity={self.severity!r}, "
            f"type={self.type!r}, "
            f"resolved={self.resolved}"
            f")>"
        )