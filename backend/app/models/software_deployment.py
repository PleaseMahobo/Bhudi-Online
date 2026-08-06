from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
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


class SoftwarePackage(Base):
    """
    Application repository entry.

    package_type: msi | exe | chocolatey | winget | custom
    """

    __tablename__ = "software_packages"
    __table_args__ = (
        Index("ix_software_packages_tenant_id", "tenant_id"),
        Index("ix_software_packages_name", "name"),
        Index("ix_software_packages_package_type", "package_type"),
        Index("ix_software_packages_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(128), nullable=False, default="1.0.0")
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # msi | exe | chocolatey | winget | custom
    package_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Download / source
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Chocolatey / Winget identifiers
    choco_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    winget_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Install / uninstall
    install_args: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # e.g. /quiet /norestart
    uninstall_args: Mapped[str | None] = mapped_column(Text, nullable=True)
    uninstall_command: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # full rollback command if needed
    success_exit_codes: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # default [0]

    # Runtime
    requires_reboot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_elevation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    architecture: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # x64 | x86 | arm64 | any

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    jobs = relationship("DeploymentJob", back_populates="package")


class DeploymentJob(Base):
    """A deployment of one package to one or more targets."""

    __tablename__ = "deployment_jobs"
    __table_args__ = (
        Index("ix_deployment_jobs_tenant_id", "tenant_id"),
        Index("ix_deployment_jobs_status", "status"),
        Index("ix_deployment_jobs_package_id", "package_id"),
        Index("ix_deployment_jobs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("software_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # install | uninstall | rollback
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="install")

    # pending | queued | running | completed | failed | cancelled | rolled_back
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional link to a previous job this one rolls back
    rollback_of_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Aggregates (updated as targets report)
    targets_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    targets_success: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    targets_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    targets_pending: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    package = relationship("SoftwarePackage", back_populates="jobs")
    targets = relationship(
        "DeploymentTarget", back_populates="job", cascade="all, delete-orphan"
    )
    events = relationship(
        "DeploymentEvent", back_populates="job", cascade="all, delete-orphan"
    )


class DeploymentTarget(Base):
    """Per-device outcome for a deployment job (success reporting)."""

    __tablename__ = "deployment_targets"
    __table_args__ = (
        Index("ix_deployment_targets_job_id", "job_id"),
        Index("ix_deployment_targets_device_id", "device_id"),
        Index("ix_deployment_targets_status", "status"),
        Index(
            "uq_deployment_target_job_device",
            "job_id",
            "device_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # soft ref if agents PK differs

    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # pending | downloading | installing | success | failed | rolled_back | skipped
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    download_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reboot_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    reported_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    job = relationship("DeploymentJob", back_populates="targets")


class DeploymentEvent(Base):
    """Chronological log for a deployment job / target."""

    __tablename__ = "deployment_events"
    __table_args__ = (
        Index("ix_deployment_events_job_id", "job_id"),
        Index("ix_deployment_events_target_id", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_targets.id", ondelete="SET NULL"),
        nullable=True,
    )

    level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="info"
    )  # debug | info | warning | error
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )

    job = relationship("DeploymentJob", back_populates="events")
