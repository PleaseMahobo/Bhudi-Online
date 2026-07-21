from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Integer, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    device_id: Mapped[str | None] = mapped_column(Text)

    title: Mapped[str | None] = mapped_column(Text)

    severity: Mapped[str | None] = mapped_column(Text)

    threat_score: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str | None] = mapped_column(
        Text,
        server_default=text("'open'::text"),
    )

    summary: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )