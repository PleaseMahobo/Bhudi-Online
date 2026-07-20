from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    device_id: Mapped[str | None] = mapped_column(Text)

    event_type: Mapped[str | None] = mapped_column(Text)

    severity: Mapped[str | None] = mapped_column(Text)

    source: Mapped[str | None] = mapped_column(Text)

    message: Mapped[str | None] = mapped_column(Text)

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )