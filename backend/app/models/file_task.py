from __future__ import annotations

import uuid

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FileTask(Base):
    __tablename__ = "file_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    device_id: Mapped[str | None] = mapped_column(Text)

    file_url: Mapped[str | None] = mapped_column(Text)

    destination: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str | None] = mapped_column(
        Text,
        server_default=text("'pending'::text"),
    )