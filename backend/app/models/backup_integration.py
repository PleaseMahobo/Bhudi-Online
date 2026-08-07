from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    BigInteger,
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


BACKUP_PROVIDERS = (
    "veeam",
    "datto",
    "acronis",
    "azure_backup",
    "backblaze",
    "onedrive",
    "google_drive",
)


class BackupProvider(Base):
    """Configured backup product integration (credentials via vault refs in config)."""

    __tablename__ = "backup_providers"
    __table_args__ = (
        Index("ix_backup_providers_tenant_id", "tenant_id"),
        Index("ix_backup_providers_provider_key", "provider_key"),
        Index("ix_backup_providers_enabled", "enabled"),
        Index(
            "uq_backup_provider_tenant_key",
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

    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    last_sync_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    jobs = relationship("BackupJob", back_populates="provider")
    resources = relationship("ProtectedResource", back_populates="provider")
    restores = relationship("RestoreJob", back_populates="provider")


class ProtectedResource(Base):
    """Device, VM, share, or cloud account under backup protection."""

    __tablename__ = "protected_resources"
    __table_args__ = (
        Index("ix_protected_resources_provider_id", "provider_id"),
        Index("ix_protected_resources_device_id", "device_id"),
        Index("ix_protected_resources_status", "status"),
        Index("ix_protected_resources_external_id", "external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backup_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="endpoint"
    )  # endpoint | vm | share | mailbox | database | cloud_account
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # protected | at_risk | unprotected | unknown
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")

    last_backup_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_backup_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_backup_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rpo_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    provider = relationship("BackupProvider", back_populates="resources")
    jobs = relationship("BackupJob", back_populates="resource")


class BackupJob(Base):
    """Scheduled or ad-hoc backup job / policy run."""

    __tablename__ = "backup_jobs"
    __table_args__ = (
        Index("ix_backup_jobs_provider_id", "provider_id"),
        Index("ix_backup_jobs_resource_id", "resource_id"),
        Index("ix_backup_jobs_status", "status"),
        Index("ix_backup_jobs_started_at", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backup_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("protected_resources.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="full"
    )  # full | incremental | differential | synthetic | cloud_sync
    schedule: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # pending | running | success | warning | failed | cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bytes_processed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    files_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    provider = relationship("BackupProvider", back_populates="jobs")
    resource = relationship("ProtectedResource", back_populates="jobs")


class RestoreJob(Base):
    """Restore request with optional automation (auto-start, post-actions)."""

    __tablename__ = "restore_jobs"
    __table_args__ = (
        Index("ix_restore_jobs_provider_id", "provider_id"),
        Index("ix_restore_jobs_resource_id", "resource_id"),
        Index("ix_restore_jobs_status", "status"),
        Index("ix_restore_jobs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backup_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("protected_resources.id", ondelete="SET NULL"),
        nullable=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # file | folder | volume | full_system | mailbox | database
    restore_type: Mapped[str] = mapped_column(String(64), nullable=False, default="file")
    source_point: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # snapshot id / point-in-time
    target_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # pending | queued | running | success | failed | cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    auto_start: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # post-restore automation hooks
    automation: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )  # e.g. {"reboot": false, "verify": true, "notify": ["ops@..."]}

    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bytes_restored: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    provider = relationship("BackupProvider", back_populates="restores")
