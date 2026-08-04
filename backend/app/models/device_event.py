from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, REAL, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeviceEvent(Base):
    __tablename__ = "device_events"

    __table_args__ = (
        Index("idx_events_device", "device_id"),
        Index("idx_events_tenant", "tenant_id"),
        Index("idx_events_type", "event_type"),
        Index("idx_events_time", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
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

    event_type: Mapped[str] = mapped_column(Text, nullable=False)

    cpu_usage: Mapped[float | None] = mapped_column(REAL)

    ram_usage: Mapped[float | None] = mapped_column(REAL)

    disk_usage: Mapped[float | None] = mapped_column(REAL)

    network_in: Mapped[float | None] = mapped_column(REAL)

    network_out: Mapped[float | None] = mapped_column(REAL)

    status: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )

    device: Mapped["Device"] = relationship(
        "Device",
        back_populates="events",
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="device_events",
    )