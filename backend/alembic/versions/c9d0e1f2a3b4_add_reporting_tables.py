"""add_reporting_tables

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-07 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("template_key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("report_type", sa.String(64), nullable=False),
        sa.Column("audience", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("default_format", sa.String(16), nullable=False, server_default="pdf"),
        sa.Column("definition", sa.JSON(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_report_templates_tenant_id", "report_templates", ["tenant_id"])
    op.create_index("ix_report_templates_report_type", "report_templates", ["report_type"])
    op.create_index("ix_report_templates_enabled", "report_templates", ["enabled"])
    op.create_index(
        "uq_report_template_tenant_key",
        "report_templates",
        ["tenant_id", "template_key"],
        unique=True,
    )

    op.create_table(
        "report_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("report_type", sa.String(64), nullable=False, server_default="custom"),
        sa.Column("audience", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_report_definitions_tenant_id", "report_definitions", ["tenant_id"])
    op.create_index("ix_report_definitions_report_type", "report_definitions", ["report_type"])
    op.create_index("ix_report_definitions_created_by", "report_definitions", ["created_by"])

    op.create_table(
        "report_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_definitions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("frequency", sa.String(32), nullable=False, server_default="weekly"),
        sa.Column("cron_hint", sa.JSON(), nullable=True),
        sa.Column("format", sa.String(16), nullable=False, server_default="pdf"),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("recipients", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(32), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_report_schedules_tenant_id", "report_schedules", ["tenant_id"])
    op.create_index("ix_report_schedules_enabled", "report_schedules", ["enabled"])
    op.create_index("ix_report_schedules_next_run_at", "report_schedules", ["next_run_at"])
    op.create_index("ix_report_schedules_template_id", "report_schedules", ["template_id"])
    op.create_index("ix_report_schedules_definition_id", "report_schedules", ["definition_id"])

    op.create_table(
        "report_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_definitions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_schedules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("report_type", sa.String(64), nullable=False),
        sa.Column("audience", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("format", sa.String(16), nullable=False, server_default="pdf"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("result_data", sa.JSON(), nullable=True),
        sa.Column("storage_uri", sa.String(1024), nullable=True),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("triggered_by", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_report_runs_tenant_id", "report_runs", ["tenant_id"])
    op.create_index("ix_report_runs_status", "report_runs", ["status"])
    op.create_index("ix_report_runs_report_type", "report_runs", ["report_type"])
    op.create_index("ix_report_runs_created_at", "report_runs", ["created_at"])
    op.create_index("ix_report_runs_template_id", "report_runs", ["template_id"])
    op.create_index("ix_report_runs_definition_id", "report_runs", ["definition_id"])
    op.create_index("ix_report_runs_schedule_id", "report_runs", ["schedule_id"])


def downgrade() -> None:
    op.drop_table("report_runs")
    op.drop_table("report_schedules")
    op.drop_table("report_definitions")
    op.drop_table("report_templates")
