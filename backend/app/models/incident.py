from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Text, func
from sqlalchemy.types import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .device import Device
    from .tenant import Tenant
    from .response_action import ResponseAction


class Incident(Base):
    __tablename__ = "incidents"

    __table_args__ = (
        Index("idx_incidents_device", "device_id"),
        Index("idx_incidents_tenant", "tenant_id"),
        Index("idx_incidents_status", "status"),
        Index("idx_incidents_severity", "severity"),
        Index("idx_incidents_created", "created_at"),
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

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    severity: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    threat_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="open",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    #
    # Relationships
    #

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="incidents",
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="incidents",
    )
    
    response_actions: Mapped[list["ResponseAction"]] = relationship(
        "ResponseAction",
         back_populates="incident",
         cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Incident("
            f"id={self.id}, "
            f"title={self.title!r}, "
            f"severity={self.severity!r}, "
            f"status={self.status!r}"
            f")>"
        )