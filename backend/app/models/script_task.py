from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ScriptTask(Base):
    __tablename__ = "script_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    script_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )

    device_id: Mapped[str | None] = mapped_column(Text)

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