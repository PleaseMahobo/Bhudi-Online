from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AutomationLog(Base):
    __tablename__ = "automation_log"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        String(36),
        nullable=True,
    )

    action: Mapped[str | None] = mapped_column(Text)

    result: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.now(),
    )