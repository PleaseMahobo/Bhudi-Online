"""add_compliance_tables

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-07 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_frameworks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("framework_key", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scope", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_frameworks_tenant_id", "compliance_frameworks", ["tenant_id"])
    op.create_index("ix_compliance_frameworks_framework_key", "compliance_frameworks", ["framework_key"])
    op.create_index("ix_compliance_frameworks_enabled", "compliance_frameworks", ["enabled"])
    op.create_index(
        "uq_compliance_framework_tenant_key",
        "compliance_frameworks",
        ["tenant_id", "framework_key"],
        unique=True,
    )

    op.create_table(
        "compliance_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("severity", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("assessment_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("automation_hints", sa.JSON(), nullable=True),
        sa.Column("guidance", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_controls_framework_id", "compliance_controls", ["framework_id"])
    op.create_index("ix_compliance_controls_control_id", "compliance_controls", ["control_id"])
    op.create_index("ix_compliance_controls_category", "compliance_controls", ["category"])
    op.create_index(
        "uq_compliance_control_framework_id",
        "compliance_controls",
        ["framework_id", "control_id"],
        unique=True,
    )

    op.create_table(
        "compliance_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("triggered_by", sa.String(255), nullable=True),
        sa.Column("total_controls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("not_applicable", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("not_assessed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("grade", sa.String(8), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_assessments_framework_id", "compliance_assessments", ["framework_id"])
    op.create_index("ix_compliance_assessments_tenant_id", "compliance_assessments", ["tenant_id"])
    op.create_index("ix_compliance_assessments_status", "compliance_assessments", ["status"])
    op.create_index("ix_compliance_assessments_started_at", "compliance_assessments", ["started_at"])

    op.create_table(
        "control_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_controls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_assessed"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("assessed_by", sa.String(255), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_control_results_assessment_id", "control_results", ["assessment_id"])
    op.create_index("ix_control_results_control_id", "control_results", ["control_id"])
    op.create_index("ix_control_results_status", "control_results", ["status"])
    op.create_index(
        "uq_control_result_assessment_control",
        "control_results",
        ["assessment_id", "control_id"],
        unique=True,
    )

    op.create_table(
        "compliance_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_controls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_assessments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("evidence_type", sa.String(64), nullable=False, server_default="document"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("storage_uri", sa.String(1024), nullable=True),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("collected_by", sa.String(255), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="valid"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_evidence_control_id", "compliance_evidence", ["control_id"])
    op.create_index("ix_compliance_evidence_assessment_id", "compliance_evidence", ["assessment_id"])
    op.create_index("ix_compliance_evidence_tenant_id", "compliance_evidence", ["tenant_id"])
    op.create_index("ix_compliance_evidence_evidence_type", "compliance_evidence", ["evidence_type"])
    op.create_index("ix_compliance_evidence_collected_at", "compliance_evidence", ["collected_at"])

    op.create_table(
        "compliance_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grade", sa.String(8), nullable=False, server_default="F"),
        sa.Column("factors", sa.JSON(), nullable=True),
        sa.Column("controls_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("controls_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("controls_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_scores_framework_id", "compliance_scores", ["framework_id"])
    op.create_index("ix_compliance_scores_tenant_id", "compliance_scores", ["tenant_id"])
    op.create_index("ix_compliance_scores_score", "compliance_scores", ["score"])
    op.create_index("ix_compliance_scores_computed_at", "compliance_scores", ["computed_at"])
    op.create_index(
        "uq_compliance_score_framework_tenant",
        "compliance_scores",
        ["framework_id", "tenant_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("compliance_scores")
    op.drop_table("compliance_evidence")
    op.drop_table("control_results")
    op.drop_table("compliance_assessments")
    op.drop_table("compliance_controls")
    op.drop_table("compliance_frameworks")
