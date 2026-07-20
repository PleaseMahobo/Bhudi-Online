from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class HuntResult(Base):
    __tablename__ = "hunt_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    hunt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )

    device_id: Mapped[str | None] = mapped_column(Text)

    matched: Mapped[bool | None] = mapped_column(Boolean)

    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )