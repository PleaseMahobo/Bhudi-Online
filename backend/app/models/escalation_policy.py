from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EscalationPolicy(Base):
    """Production-grade Escalation Policy definition."""

    __tablename__ = "escalation_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Example levels structure:
    # [
    #   {"repeat_count": 1, "severity": "warning", "notify": ["email"]},
    #   {"repeat_count": 3, "severity": "critical", "notify": ["email", "slack"]},
    #   {"repeat_count": 5, "severity": "critical", "notify": ["pagerduty"]}
    # ]
    levels: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    rules = relationship("AlertRule", back_populates="escalation_policy")
