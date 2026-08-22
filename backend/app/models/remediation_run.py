from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, String, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RemediationRun(Base):
    """Audit trail for alert-triggered remediation attempts."""

    __tablename__ = "remediation_runs"
    __table_args__ = (
        Index("ix_remediation_runs_fingerprint", "fingerprint"),
        Index("ix_remediation_runs_alert", "alert_id"),
        Index("ix_remediation_runs_created", "created_at"),
        Index("ix_remediation_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    alert_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rule_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    fingerprint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    correlation_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    command_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")

    skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)

    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    command_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
