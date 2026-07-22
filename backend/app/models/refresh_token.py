from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .user import User


class RefreshToken(Base):
    """
    Persisted refresh token.

    Only the SHA-256 hash of the JWT is stored.
    The plaintext refresh token is never persisted.
    """

    __tablename__ = "refresh_tokens"

    # =====================================================
    # Identity
    # =====================================================

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =====================================================
    # Token Information
    # =====================================================

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    jwt_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    token_family: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    generation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # =====================================================
    # Lifetime
    # =====================================================

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =====================================================
    # Revocation
    # =====================================================

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id"),
        nullable=True,
    )

    # =====================================================
    # Device Information
    # =====================================================

    ip_address: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # =====================================================
    # Relationships
    # =====================================================

    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
    )

    replacement: Mapped["RefreshToken | None"] = relationship(
        "RefreshToken",
        remote_side=[id],
        uselist=False,
        backref="previous_token",
    )

    # =====================================================
    # Convenience Properties
    # =====================================================

    @property
    def is_active(self) -> bool:
        return (
            not self.revoked
            and self.expires_at > datetime.now(timezone.utc)
        )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_replaced(self) -> bool:
        return self.replaced_by_token_id is not None

    # =====================================================
    # State Changes
    # =====================================================

    def mark_used(self) -> None:
        self.last_used_at = datetime.now(timezone.utc)

    def revoke(self, reason: str | None = None) -> None:
        self.revoked = True
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_reason = reason

    def __repr__(self) -> str:
        return (
            f"<RefreshToken("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"revoked={self.revoked}"
            f")>"
        )