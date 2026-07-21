from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Command(Base):
    __tablename__ = "commands"

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

    command: Mapped[str | None] = mapped_column(Text)

    args: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    status: Mapped[str | None] = mapped_column(
        Text,
        server_default=text("'pending'::text"),
    )

    output: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )

    executed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="commands",
    )