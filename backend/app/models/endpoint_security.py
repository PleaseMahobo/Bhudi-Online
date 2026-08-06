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


# Canonical vendor keys used across the platform
SECURITY_PROVIDERS = (
    "windows_defender",
    "microsoft_defender_xdr",
    "threatlocker",
    "huntress",
    "sentinelone",
    "crowdstrike",
    "bitdefender",
    "sophos",
    "malwarebytes",
)


class SecurityProvider(Base):
    """
    Configured endpoint-security product integration.

    provider_key must be one of SECURITY_PROVIDERS (or a documented extension).
    Credentials are stored as opaque JSON references (secret names / vault paths),
    never as raw API keys in application logs.
    """

    __tablename__ = "security_providers"
    __table_args__ = (
        Index("ix_security_providers_tenant_id", "tenant_id"),
        Index("ix_security_providers_provider_key", "provider_key"),
        Index("ix_security_providers_enabled", "enabled"),
        Index(
            "uq_security_provider_tenant_key",
            "tenant_id",
            "provider_key",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Opaque credential / connection config (vault refs, region, tenant IDs)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Sync health
    last_sync_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_sync_status: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # ok | error | never
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    agents = relationship("EndpointSecurityAgent", back_populates="provider")
    findings = relationship("SecurityFinding", back_populates="provider")


class EndpointSecurityAgent(Base):
    """Per-device presence and health of a security product agent."""

    __tablename__ = "endpoint_security_agents"
    __table_args__ = (
        Index("ix_endpoint_security_agents_device_id", "device_id"),
        Index("ix_endpoint_security_agents_provider_id", "provider_id"),
        Index("ix_endpoint_security_agents_status", "status"),
        Index(
            "uq_endpoint_security_agent_device_provider",
            "device_id",
            "provider_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=True
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_providers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # External product identifiers
    external_agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # healthy | degraded | offline | not_installed | unknown
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")

    real_time_protection: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    definitions_up_to_date: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_scan_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Product-specific telemetry snapshot
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    provider = relationship("SecurityProvider", back_populates="agents")


class SecurityFinding(Base):
    """Threat / detection / policy finding from an endpoint security product."""

    __tablename__ = "security_findings"
    __table_args__ = (
        Index("ix_security_findings_device_id", "device_id"),
        Index("ix_security_findings_provider_id", "provider_id"),
        Index("ix_security_findings_severity", "severity"),
        Index("ix_security_findings_status", "status"),
        Index("ix_security_findings_detected_at", "detected_at"),
        Index("ix_security_findings_external_id", "external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # critical | high | medium | low | info
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    # open | investigating | contained | resolved | false_positive
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")

    category: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # malware | ransomware | pua | policy | exploit | ...
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    detected_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    provider = relationship("SecurityProvider", back_populates="findings")


class EndpointSecurityScore(Base):
    """
    Computed security posture score for a device (0–100).

    Factors are stored for transparency / audit.
    """

    __tablename__ = "endpoint_security_scores"
    __table_args__ = (
        Index("ix_endpoint_security_scores_device_id", "device_id"),
        Index("ix_endpoint_security_scores_score", "score"),
        Index("ix_endpoint_security_scores_computed_at", "computed_at"),
        Index(
            "uq_endpoint_security_score_device",
            "device_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0–100
    grade: Mapped[str] = mapped_column(
        String(8), nullable=False, default="F"
    )  # A–F

    # Transparent breakdown
    factors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    open_critical: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_high: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agents_healthy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agents_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
