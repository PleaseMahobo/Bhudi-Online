from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .tenant import Tenant


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    hostname: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        server_default="offline",
    )

    last_seen: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=func.now(),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
    )

    tenant: Mapped["Tenant | None"] = relationship(
        back_populates="agents",
    )

    def __repr__(self) -> str:
        return (
            f"<Agent("
            f"id={self.id}, "
            f"hostname={self.hostname!r}, "
            f"status={self.status!r}"
            f")>"
        )