"""add_software_deployment_tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-06 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "software_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(128), nullable=False, server_default="1.0.0"),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("package_type", sa.String(32), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("file_name", sa.String(512), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("choco_id", sa.String(255), nullable=True),
        sa.Column("winget_id", sa.String(255), nullable=True),
        sa.Column("install_args", sa.Text(), nullable=True),
        sa.Column("uninstall_args", sa.Text(), nullable=True),
        sa.Column("uninstall_command", sa.Text(), nullable=True),
        sa.Column("success_exit_codes", sa.JSON(), nullable=True),
        sa.Column("requires_reboot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_elevation", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("architecture", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_software_packages_tenant_id", "software_packages", ["tenant_id"])
    op.create_index("ix_software_packages_name", "software_packages", ["name"])
    op.create_index("ix_software_packages_package_type", "software_packages", ["package_type"])
    op.create_index("ix_software_packages_is_active", "software_packages", ["is_active"])

    op.create_table(
        "deployment_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("software_packages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("action", sa.String(32), nullable=False, server_default="install"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rollback_of_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deployment_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("targets_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("targets_success", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("targets_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("targets_pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_deployment_jobs_tenant_id", "deployment_jobs", ["tenant_id"])
    op.create_index("ix_deployment_jobs_status", "deployment_jobs", ["status"])
    op.create_index("ix_deployment_jobs_package_id", "deployment_jobs", ["package_id"])
    op.create_index("ix_deployment_jobs_created_at", "deployment_jobs", ["created_at"])

    op.create_table(
        "deployment_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deployment_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("download_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("reboot_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_deployment_targets_job_id", "deployment_targets", ["job_id"])
    op.create_index("ix_deployment_targets_device_id", "deployment_targets", ["device_id"])
    op.create_index("ix_deployment_targets_status", "deployment_targets", ["status"])
    op.create_index("uq_deployment_target_job_device", "deployment_targets", ["job_id", "device_id"], unique=True)

    op.create_table(
        "deployment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deployment_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deployment_targets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("level", sa.String(16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_deployment_events_job_id", "deployment_events", ["job_id"])
    op.create_index("ix_deployment_events_target_id", "deployment_events", ["target_id"])


def downgrade() -> None:
    op.drop_table("deployment_events")
    op.drop_table("deployment_targets")
    op.drop_table("deployment_jobs")
    op.drop_table("software_packages")
