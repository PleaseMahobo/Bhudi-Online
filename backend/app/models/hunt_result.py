from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Text, text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .threat_hunt import ThreatHunt


class HuntResult(Base):
    __tablename__ = "hunt_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    hunt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("threat_hunts.id", ondelete="CASCADE"),
        nullable=False,
    )

    device_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    matched: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    evidence: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    #
    # Relationships
    #

    hunt: Mapped["ThreatHunt"] = relationship(
        "ThreatHunt",
        back_populates="results",
    )

    def __repr__(self) -> str:
        return (
            f"<HuntResult("
            f"id={self.id}, "
            f"hunt_id={self.hunt_id}, "
            f"matched={self.matched}"
            f")>"
        )