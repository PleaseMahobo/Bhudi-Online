from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


REPORT_TYPES = (
    "executive",
    "customer",
    "technician",
    "patch_compliance",
    "security_compliance",
    "asset",
    "custom",
)

REPORT_FORMATS = ("pdf", "excel", "csv", "json")

REPORT_AUDIENCES = ("executive", "customer", "technician", "internal")

SCHEDULE_FREQUENCIES = ("hourly", "daily", "weekly", "monthly", "quarterly")

RUN_STATUSES = (
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
)


class ReportTemplate(Base):
    """Built-in or tenant-custom report template."""

    __tablename__ = "report_templates"
    __table_args__ = (
        Index("ix_report_templates_tenant_id", "tenant_id"),
        Index("ix_report_templates_report_type", "report_type"),
        Index("ix_report_templates_enabled", "enabled"),
        Index(
            "uq_report_template_tenant_key",
            "tenant_id",
            "template_key",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    default_format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")

    definition: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    runs = relationship("ReportRun", back_populates="template")
    schedules = relationship("ReportSchedule", back_populates="template")


class ReportDefinition(Base):
    """User-defined custom report configuration."""

    __tablename__ = "report_definitions"
    __table_args__ = (
        Index("ix_report_definitions_tenant_id", "tenant_id"),
        Index("ix_report_definitions_report_type", "report_type"),
        Index("ix_report_definitions_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False, default="custom")
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")

    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    runs = relationship("ReportRun", back_populates="definition")
    schedules = relationship("ReportSchedule", back_populates="definition")


class ReportRun(Base):
    """Single report generation execution."""

    __tablename__ = "report_runs"
    __table_args__ = (
        Index("ix_report_runs_tenant_id", "tenant_id"),
        Index("ix_report_runs_status", "status"),
        Index("ix_report_runs_report_type", "report_type"),
        Index("ix_report_runs_created_at", "created_at"),
        Index("ix_report_runs_template_id", "template_id"),
        Index("ix_report_runs_definition_id", "definition_id"),
        Index("ix_report_runs_schedule_id", "schedule_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_schedules.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    storage_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    template = relationship("ReportTemplate", back_populates="runs")
    definition = relationship("ReportDefinition", back_populates="runs")
    schedule = relationship(
        "ReportSchedule", back_populates="runs", foreign_keys=[schedule_id]
    )


class ReportSchedule(Base):
    """Recurring report generation schedule."""

    __tablename__ = "report_schedules"
    __table_args__ = (
        Index("ix_report_schedules_tenant_id", "tenant_id"),
        Index("ix_report_schedules_enabled", "enabled"),
        Index("ix_report_schedules_next_run_at", "next_run_at"),
        Index("ix_report_schedules_template_id", "template_id"),
        Index("ix_report_schedules_definition_id", "definition_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="weekly")
    cron_hint: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    recipients: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_run_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_run_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    template = relationship("ReportTemplate", back_populates="schedules")
    definition = relationship("ReportDefinition", back_populates="schedules")
    runs = relationship(
        "ReportRun",
        back_populates="schedule",
        foreign_keys="ReportRun.schedule_id",
    )


SYSTEM_TEMPLATES: list[dict[str, Any]] = [
    {
        "template_key": "executive_overview",
        "name": "Executive Overview Dashboard",
        "description": "Fleet health, security posture, open incidents, patch and compliance scores",
        "report_type": "executive",
        "audience": "executive",
        "default_format": "pdf",
        "definition": {
            "sections": [
                "fleet_summary",
                "security_score",
                "patch_compliance",
                "open_incidents",
                "compliance_posture",
                "backup_health",
            ]
        },
    },
    {
        "template_key": "customer_sla",
        "name": "Customer SLA Report",
        "description": "Uptime, ticket resolution, response times for customer delivery",
        "report_type": "customer",
        "audience": "customer",
        "default_format": "pdf",
        "definition": {
            "sections": ["uptime", "tickets_resolved", "mttr", "open_tickets", "assets"]
        },
    },
    {
        "template_key": "technician_workload",
        "name": "Technician Workload Report",
        "description": "Assigned tickets, pending patches, alerts, device health for techs",
        "report_type": "technician",
        "audience": "technician",
        "default_format": "excel",
        "definition": {
            "sections": [
                "my_tickets",
                "pending_patches",
                "critical_alerts",
                "offline_devices",
                "upcoming_maintenance",
            ]
        },
    },
    {
        "template_key": "patch_compliance",
        "name": "Patch Compliance Report",
        "description": "OS/app patch status across the fleet",
        "report_type": "patch_compliance",
        "audience": "internal",
        "default_format": "excel",
        "definition": {
            "sections": ["summary", "by_os", "critical_missing", "device_detail"]
        },
    },
    {
        "template_key": "security_compliance",
        "name": "Security Compliance Report",
        "description": "Endpoint security scores, findings, framework posture",
        "report_type": "security_compliance",
        "audience": "executive",
        "default_format": "pdf",
        "definition": {
            "sections": [
                "endpoint_scores",
                "open_findings",
                "framework_scores",
                "evidence_gaps",
            ]
        },
    },
    {
        "template_key": "asset_inventory",
        "name": "Asset Inventory Report",
        "description": "Hardware, software, licenses, lifecycle status",
        "report_type": "asset",
        "audience": "internal",
        "default_format": "csv",
        "definition": {
            "sections": ["hardware", "software", "licenses", "warranty_expiry"]
        },
    },
]
