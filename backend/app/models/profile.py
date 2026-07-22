from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .tenant import Tenant
    from .user import User


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'technician'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    #
    # Relationships
    #

    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
        uselist=False,
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="profiles",
    )

    def __repr__(self) -> str:
        return (
            f"<Profile("
            f"id={self.id}, "
            f"email={self.email!r}"
            f")>"
        )