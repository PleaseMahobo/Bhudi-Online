"""add_backup_integration_tables

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-07 02:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backup_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(32), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_backup_providers_tenant_id", "backup_providers", ["tenant_id"])
    op.create_index("ix_backup_providers_provider_key", "backup_providers", ["provider_key"])
    op.create_index("ix_backup_providers_enabled", "backup_providers", ["enabled"])
    op.create_index(
        "uq_backup_provider_tenant_key",
        "backup_providers",
        ["tenant_id", "provider_key"],
        unique=True,
    )

    op.create_table(
        "protected_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backup_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False, server_default="endpoint"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("last_backup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_backup_status", sa.String(32), nullable=True),
        sa.Column("last_backup_bytes", sa.BigInteger(), nullable=True),
        sa.Column("rpo_hours", sa.Float(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_protected_resources_provider_id", "protected_resources", ["provider_id"])
    op.create_index("ix_protected_resources_device_id", "protected_resources", ["device_id"])
    op.create_index("ix_protected_resources_status", "protected_resources", ["status"])
    op.create_index("ix_protected_resources_external_id", "protected_resources", ["external_id"])

    op.create_table(
        "backup_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backup_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("protected_resources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("job_type", sa.String(64), nullable=False, server_default="full"),
        sa.Column("schedule", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("bytes_processed", sa.BigInteger(), nullable=True),
        sa.Column("files_processed", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_backup_jobs_provider_id", "backup_jobs", ["provider_id"])
    op.create_index("ix_backup_jobs_resource_id", "backup_jobs", ["resource_id"])
    op.create_index("ix_backup_jobs_status", "backup_jobs", ["status"])
    op.create_index("ix_backup_jobs_started_at", "backup_jobs", ["started_at"])

    op.create_table(
        "restore_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backup_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("protected_resources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("restore_type", sa.String(64), nullable=False, server_default="file"),
        sa.Column("source_point", sa.String(255), nullable=True),
        sa.Column("target_path", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("auto_start", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("automation", sa.JSON(), nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("bytes_restored", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_restore_jobs_provider_id", "restore_jobs", ["provider_id"])
    op.create_index("ix_restore_jobs_resource_id", "restore_jobs", ["resource_id"])
    op.create_index("ix_restore_jobs_status", "restore_jobs", ["status"])
    op.create_index("ix_restore_jobs_created_at", "restore_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("restore_jobs")
    op.drop_table("backup_jobs")
    op.drop_table("protected_resources")
    op.drop_table("backup_providers")
