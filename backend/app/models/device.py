from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from .action import Action
    from .alert import Alert
    from .device_event import DeviceEvent
    from .device_heartbeat import DeviceHeartbeat
    from .device_metric import DeviceMetric
    from .tenant import Tenant


class Device(Base):
    __tablename__ = "devices"

    __table_args__ = (
        Index("idx_devices_health", "health_score"),
        Index("idx_devices_last_seen", "last_seen"),
        Index("idx_devices_status", "status"),
        Index("idx_devices_tenant", "tenant_id"),
    )

    hostname: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ip: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        server_default="offline",
    )

    cpu: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ram: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    disk: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    agent_version: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    last_seen: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=func.now(),
    )

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=func.now(),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
    )

    agent_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    consecutive_misses: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        server_default="0",
    )

    health_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        server_default="100",
    )

    missed_heartbeats: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        server_default="0",
    )

    ip_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    os: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    version: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tenant: Mapped["Tenant | None"] = relationship(
        back_populates="devices",
    )

    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="device",
    )

    actions: Mapped[list["Action"]] = relationship(
        back_populates="device",
    )

    events: Mapped[list["DeviceEvent"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )

    heartbeats: Mapped[list["DeviceHeartbeat"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )

    metrics: Mapped[list["DeviceMetric"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Device("
            f"id={self.id}, "
            f"hostname={self.hostname!r}, "
            f"status={self.status!r}"
            f")>"
        )