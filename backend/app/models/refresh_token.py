from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base):
    """
    Enterprise Refresh Token model.

    Features
    --------
    • Secure refresh token rotation
    • Replay attack detection
    • Token families
    • Session tracking
    • Device tracking
    • Audit trail
    • Logout-all support
    """

    __tablename__ = "refresh_tokens"

    __table_args__ = (

        CheckConstraint(
            "generation >= 1",
            name="ck_refresh_token_generation",
        ),

        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_refresh_token_risk_score",
        ),

        Index(
            "ix_refresh_token_user_active",
            "user_id",
            "revoked",
            "expires_at",
        ),

        Index(
            "ix_refresh_token_family_generation",
            "token_family",
            "generation",
        ),

        Index(
            "ix_refresh_token_session_generation",
            "session_id",
            "generation",
        ),
    )


    # =====================================================
    # Identity
    # =====================================================

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # =====================================================
    # Refresh Token Metadata
    # =====================================================

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )


    jwt_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
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
        server_default="1",
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
    # Revocation Metadata
    # =====================================================

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
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
        String(36),
        ForeignKey(
            "refresh_tokens.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
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


    device_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )


    operating_system: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )


    browser: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )


    browser_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )


    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


    # =====================================================
    # Security Metadata
    # =====================================================

    login_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="password",
    )


    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )


    trusted_device: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )


    # =====================================================
    # Relationships
    # =====================================================

    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
        lazy="joined",
    )


    replacement: Mapped["RefreshToken | None"] = relationship(
        "RefreshToken",
        remote_side="RefreshToken.id",
        uselist=False,
        foreign_keys=[replaced_by_token_id],
    )


    # =====================================================
    # Convenience Properties
    # =====================================================

    @property
    def is_active(self) -> bool:
        return (
            not self.revoked
            and datetime.now(timezone.utc) < self.expires_at
        )


    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


    @property
    def is_revoked(self) -> bool:
        return self.revoked


    @property
    def is_rotated(self) -> bool:
        return self.replaced_by_token_id is not None


    @property
    def can_rotate(self) -> bool:
        return (
            self.is_active
            and not self.is_rotated
        )


    @property
    def age_seconds(self) -> int:
        return int(
            (
                datetime.now(timezone.utc)
                - self.created_at
            ).total_seconds()
        )


    # =====================================================
    # Lifecycle Methods
    # =====================================================

    def mark_used(self) -> None:
        self.last_used_at = datetime.now(timezone.utc)


    def revoke(
        self,
        reason: str | None = None,
    ) -> None:

        if self.revoked:
            return

        now = datetime.now(timezone.utc)

        self.revoked = True
        self.revoked_at = now
        self.revoked_reason = reason
        self.updated_at = now


    def rotate_to(
        self,
        replacement: "RefreshToken",
    ) -> None:

        self.revoke(
            "token_rotated"
        )

        self.replaced_by_token_id = replacement.id

        self.updated_at = datetime.now(timezone.utc)


    def trust_device(self) -> None:

        self.trusted_device = True

        self.updated_at = datetime.now(timezone.utc)


    def update_risk_score(
        self,
        score: int,
    ) -> None:

        self.risk_score = score

        self.updated_at = datetime.now(timezone.utc)


    # =====================================================
    # Serialization Helpers
    # =====================================================

    def to_dict(self) -> dict:

        return {

            "id": str(self.id),

            "user_id": str(self.user_id),

            "jwt_id": self.jwt_id,

            "session_id": self.session_id,

            "token_family": self.token_family,

            "generation": self.generation,

            "created_at": self.created_at.isoformat(),

            "updated_at": self.updated_at.isoformat(),

            "last_used_at": (
                self.last_used_at.isoformat()
                if self.last_used_at
                else None
            ),

            "expires_at": self.expires_at.isoformat(),

            "revoked": self.revoked,

            "revoked_at": (
                self.revoked_at.isoformat()
                if self.revoked_at
                else None
            ),

            "revoked_reason": self.revoked_reason,

            "device_name": self.device_name,

            "device_id": self.device_id,

            "trusted_device": self.trusted_device,

            "risk_score": self.risk_score,

            "active": self.is_active,

            "expired": self.is_expired,

            "rotated": self.is_rotated,
        }


    # =====================================================
    # Debug Representation
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<RefreshToken(id={self.id!r}, user_id={self.user_id!r}, "
            f"session={self.session_id!r}, generation={self.generation}, "
            f"revoked={self.revoked}, expires_at={self.expires_at.isoformat()})>"
        )

    # =====================================================
    # Equality
    # =====================================================

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if self is other:
            return True
        if not isinstance(other, RefreshToken):
            return False

        return self.id == other.id

    def __hash__(self) -> int:
        return hash((RefreshToken, self.id))
