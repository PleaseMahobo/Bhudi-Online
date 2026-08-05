from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AlertRule(Base):
    """Production-grade Alert Rule definition."""

    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Matching criteria
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    check_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metric_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Thresholds
    warning_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Anomaly detection
    anomaly_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_tolerance: Mapped[float | None] = mapped_column(Float, nullable=True)

    # State change detection
    state_change_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Suppression
    ai_suppression_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    maintenance_window_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Escalation
    escalation_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("escalation_policies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Control
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)  # lower = higher priority

    # Metadata
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    escalation_policy = relationship("EscalationPolicy", back_populates="rules")
