from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device import Device


class DeviceHeartbeat(Base):
    __tablename__ = "device_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),  # cspell:ignore ondelete
    )

    status: Mapped[str | None] = mapped_column(Text)

    cpu: Mapped[Decimal | None] = mapped_column(Numeric)

    ram: Mapped[Decimal | None] = mapped_column(Numeric)

    disk: Mapped[Decimal | None] = mapped_column(Numeric)

    ip: Mapped[str | None] = mapped_column(Text)

    timestamp: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="heartbeats",
    )