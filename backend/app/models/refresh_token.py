from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class RefreshToken(Base):
    """
    Persisted refresh token.

    Only a SHA-256 hash of the JWT is stored.
    The plaintext refresh token never touches
    persistent storage.
    """

    __tablename__ = "refresh_tokens"

    # =====================================================
    # Identity
    # =====================================================

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
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

    token_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    jwt_id = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    session_id = Column(
        String(64),
        nullable=False,
        index=True,
    )

    token_family = Column(
        String(64),
        nullable=False,
        index=True,
    )

    generation = Column(
        Integer,
        nullable=False,
        default=1,
    )

    # =====================================================
    # Lifetime
    # =====================================================

    expires_at = Column(
        DateTime,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    last_used_at = Column(
        DateTime,
        nullable=True,
    )

    # =====================================================
    # Revocation
    # =====================================================

    revoked = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    revoked_at = Column(
        DateTime,
        nullable=True,
    )

    revoked_reason = Column(
        String(100),
        nullable=True,
    )

    replaced_by_token_id = Column(
        UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id"),
        nullable=True,
    )

    # =====================================================
    # Device Information
    # =====================================================

    ip_address = Column(
        String(64),
        nullable=True,
    )

    user_agent = Column(
        String(512),
        nullable=True,
    )

    device_name = Column(
        String(255),
        nullable=True,
    )

    # =====================================================
    # Relationships
    # =====================================================

    user = relationship(
        "User",
        back_populates="refresh_tokens",
    )

    replacement = relationship(
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
            and self.expires_at > datetime.utcnow()
        )

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    @property
    def is_replaced(self) -> bool:
        return self.replaced_by_token_id is not None

    # =====================================================
    # State Changes
    # =====================================================

    def mark_used(self) -> None:
        self.last_used_at = datetime.utcnow()

    def revoke(
        self,
        reason: str | None = None,
    ) -> None:
        self.revoked = True
        self.revoked_at = datetime.utcnow()
        self.revoked_reason = reason