"""add_endpoint_security_tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-07 01:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_providers",
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
    op.create_index("ix_security_providers_tenant_id", "security_providers", ["tenant_id"])
    op.create_index("ix_security_providers_provider_key", "security_providers", ["provider_key"])
    op.create_index("ix_security_providers_enabled", "security_providers", ["enabled"])
    op.create_index(
        "uq_security_provider_tenant_key",
        "security_providers",
        ["tenant_id", "provider_key"],
        unique=True,
    )

    op.create_table(
        "endpoint_security_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("security_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_agent_id", sa.String(255), nullable=True),
        sa.Column("agent_version", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("real_time_protection", sa.Boolean(), nullable=True),
        sa.Column("definitions_up_to_date", sa.Boolean(), nullable=True),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_endpoint_security_agents_device_id", "endpoint_security_agents", ["device_id"])
    op.create_index("ix_endpoint_security_agents_provider_id", "endpoint_security_agents", ["provider_id"])
    op.create_index("ix_endpoint_security_agents_status", "endpoint_security_agents", ["status"])
    op.create_index(
        "uq_endpoint_security_agent_device_provider",
        "endpoint_security_agents",
        ["device_id", "provider_id"],
        unique=True,
    )

    op.create_table(
        "security_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("security_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_security_findings_device_id", "security_findings", ["device_id"])
    op.create_index("ix_security_findings_provider_id", "security_findings", ["provider_id"])
    op.create_index("ix_security_findings_severity", "security_findings", ["severity"])
    op.create_index("ix_security_findings_status", "security_findings", ["status"])
    op.create_index("ix_security_findings_detected_at", "security_findings", ["detected_at"])
    op.create_index("ix_security_findings_external_id", "security_findings", ["external_id"])

    op.create_table(
        "endpoint_security_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grade", sa.String(8), nullable=False, server_default="F"),
        sa.Column("factors", sa.JSON(), nullable=True),
        sa.Column("open_critical", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_high", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agents_healthy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agents_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_endpoint_security_scores_device_id", "endpoint_security_scores", ["device_id"])
    op.create_index("ix_endpoint_security_scores_score", "endpoint_security_scores", ["score"])
    op.create_index("ix_endpoint_security_scores_computed_at", "endpoint_security_scores", ["computed_at"])
    op.create_index("uq_endpoint_security_score_device", "endpoint_security_scores", ["device_id"], unique=True)


def downgrade() -> None:
    op.drop_table("endpoint_security_scores")
    op.drop_table("security_findings")
    op.drop_table("endpoint_security_agents")
    op.drop_table("security_providers")
