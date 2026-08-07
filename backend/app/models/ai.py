from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


AI_TASK_TYPES = (
    "root_cause",
    "script_generation",
    "remediation",
    "ticket_summary",
    "knowledge",
    "predictive_failure",
    "capacity_forecast",
)


class AIRun(Base):
    """Audit log of an AI inference request/response."""

    __tablename__ = "ai_runs"
    __table_args__ = (
        Index("ix_ai_runs_tenant_id", "tenant_id"),
        Index("ix_ai_runs_task_type", "task_type"),
        Index("ix_ai_runs_status", "status"),
        Index("ix_ai_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )

    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # pending | completed | failed | dry_run
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class KnowledgeArticle(Base):
    """AI / technician knowledge base entry."""

    __tablename__ = "knowledge_articles"
    __table_args__ = (
        Index("ix_knowledge_articles_tenant_id", "tenant_id"),
        Index("ix_knowledge_articles_slug", "slug"),
        Index("ix_knowledge_articles_published", "published"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    embedding_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class PredictionRecord(Base):
    """Predictive failure / capacity forecast snapshot."""

    __tablename__ = "prediction_records"
    __table_args__ = (
        Index("ix_prediction_records_tenant_id", "tenant_id"),
        Index("ix_prediction_records_kind", "kind"),
        Index("ix_prediction_records_target_id", "target_id"),
        Index("ix_prediction_records_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )

    # predictive_failure | capacity_forecast
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    horizon_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
