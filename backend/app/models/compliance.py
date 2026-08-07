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


# Canonical framework keys used across the platform
COMPLIANCE_FRAMEWORKS = (
    "cis",
    "iso27001",
    "pci_dss",
    "hipaa",
    "gdpr",
    "nist",
    "soc2",
)

FRAMEWORK_CATALOG: list[dict[str, str]] = [
    {"framework_key": "cis", "display_name": "CIS Controls", "version": "v8"},
    {"framework_key": "iso27001", "display_name": "ISO/IEC 27001", "version": "2022"},
    {"framework_key": "pci_dss", "display_name": "PCI DSS", "version": "4.0"},
    {"framework_key": "hipaa", "display_name": "HIPAA Security Rule", "version": "45 CFR"},
    {"framework_key": "gdpr", "display_name": "GDPR", "version": "2016/679"},
    {"framework_key": "nist", "display_name": "NIST CSF", "version": "2.0"},
    {"framework_key": "soc2", "display_name": "SOC 2", "version": "TSC 2017"},
]


class ComplianceFramework(Base):
    """Enabled compliance framework for a tenant (or global catalog seed)."""

    __tablename__ = "compliance_frameworks"
    __table_args__ = (
        Index("ix_compliance_frameworks_tenant_id", "tenant_id"),
        Index("ix_compliance_frameworks_framework_key", "framework_key"),
        Index("ix_compliance_frameworks_enabled", "enabled"),
        Index(
            "uq_compliance_framework_tenant_key",
            "tenant_id",
            "framework_key",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    framework_key: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    scope: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    controls = relationship("ComplianceControl", back_populates="framework")
    assessments = relationship("ComplianceAssessment", back_populates="framework")
    scores = relationship("ComplianceScore", back_populates="framework")


class ComplianceControl(Base):
    """Individual control / requirement within a framework."""

    __tablename__ = "compliance_controls"
    __table_args__ = (
        Index("ix_compliance_controls_framework_id", "framework_id"),
        Index("ix_compliance_controls_control_id", "control_id"),
        Index("ix_compliance_controls_category", "category"),
        Index(
            "uq_compliance_control_framework_id",
            "framework_id",
            "control_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
    )

    control_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    assessment_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual"
    )

    automation_hints: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    guidance: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    framework = relationship("ComplianceFramework", back_populates="controls")
    results = relationship("ControlResult", back_populates="control")
    evidence = relationship("ComplianceEvidence", back_populates="control")


class ComplianceAssessment(Base):
    """A point-in-time assessment run against a framework scope."""

    __tablename__ = "compliance_assessments"
    __table_args__ = (
        Index("ix_compliance_assessments_framework_id", "framework_id"),
        Index("ix_compliance_assessments_tenant_id", "tenant_id"),
        Index("ix_compliance_assessments_status", "status"),
        Index("ix_compliance_assessments_started_at", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    total_controls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_applicable: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_assessed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(8), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    framework = relationship("ComplianceFramework", back_populates="assessments")
    results = relationship("ControlResult", back_populates="assessment")


class ControlResult(Base):
    """Per-control outcome within an assessment."""

    __tablename__ = "control_results"
    __table_args__ = (
        Index("ix_control_results_assessment_id", "assessment_id"),
        Index("ix_control_results_control_id", "control_id"),
        Index("ix_control_results_status", "status"),
        Index(
            "uq_control_result_assessment_control",
            "assessment_id",
            "control_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_controls.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_assessed"
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assessed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    assessment = relationship("ComplianceAssessment", back_populates="results")
    control = relationship("ComplianceControl", back_populates="results")


class ComplianceEvidence(Base):
    """Evidence artifact linked to a control (and optionally an assessment)."""

    __tablename__ = "compliance_evidence"
    __table_args__ = (
        Index("ix_compliance_evidence_control_id", "control_id"),
        Index("ix_compliance_evidence_assessment_id", "assessment_id"),
        Index("ix_compliance_evidence_tenant_id", "tenant_id"),
        Index("ix_compliance_evidence_evidence_type", "evidence_type"),
        Index("ix_compliance_evidence_collected_at", "collected_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_controls.id", ondelete="CASCADE"),
        nullable=False,
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_assessments.id", ondelete="SET NULL"),
        nullable=True,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    evidence_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="document"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    storage_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    collected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="valid")

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    control = relationship("ComplianceControl", back_populates="evidence")


class ComplianceScore(Base):
    """Computed compliance posture score for a framework (0–100)."""

    __tablename__ = "compliance_scores"
    __table_args__ = (
        Index("ix_compliance_scores_framework_id", "framework_id"),
        Index("ix_compliance_scores_tenant_id", "tenant_id"),
        Index("ix_compliance_scores_score", "score"),
        Index("ix_compliance_scores_computed_at", "computed_at"),
        Index(
            "uq_compliance_score_framework_tenant",
            "framework_id",
            "tenant_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grade: Mapped[str] = mapped_column(String(8), nullable=False, default="F")

    factors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    controls_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    controls_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    controls_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    computed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    framework = relationship("ComplianceFramework", back_populates="scores")
