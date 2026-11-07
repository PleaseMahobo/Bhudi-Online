from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Text, String, Uuid, text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Match Incident.id (String(36)) — not Uuid — so FK joins work on SQLite and Postgres.
    incident_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )

    device_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    severity: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentTimeline("
            f"id={self.id}, "
            f"incident_id={self.incident_id}, "
            f"event_type={self.event_type!r}"
            f")>"
        )
