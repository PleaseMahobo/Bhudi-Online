from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .hunt_result import HuntResult


class ThreatHunt(Base):
    __tablename__ = "threat_hunts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    hunt_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    indicator: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'pending'"),
    )

    created_by: Mapped[str | None] = mapped_column(
        Text,
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

    results: Mapped[list["HuntResult"]] = relationship(
        "HuntResult",
        back_populates="hunt",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ThreatHunt("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"status={self.status!r}"
            f")>"
        )