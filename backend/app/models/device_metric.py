from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeviceMetric(Base):
    __tablename__ = "device_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id"),
        nullable=True,
    )

    cpu_usage: Mapped[Decimal | None] = mapped_column(Numeric)

    ram_usage: Mapped[Decimal | None] = mapped_column(Numeric)

    disk_usage: Mapped[Decimal | None] = mapped_column(Numeric)

    recorded_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
    )

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="metrics",
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="device_metrics",
    )