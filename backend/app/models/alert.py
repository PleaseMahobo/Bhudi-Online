from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Alert(Base):
    __tablename__ = "alerts"

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

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
    )

    type: Mapped[str | None] = mapped_column(Text)

    severity: Mapped[str | None] = mapped_column(Text)

    message: Mapped[str | None] = mapped_column(Text)

    resolved: Mapped[bool | None] = mapped_column(
        Boolean,
        server_default=text("false"),
    )

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )

    threat_score: Mapped[int | None] = mapped_column(Integer)

    mitre_id: Mapped[str | None] = mapped_column(Text)

    mitre_name: Mapped[str | None] = mapped_column(Text)

    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="alerts",
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="alerts",
    )