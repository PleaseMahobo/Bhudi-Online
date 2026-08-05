"""add_alert_engine_tables

Revision ID: a1b2c3d4e5f6
Revises: 6d8b56c8a6cf
Create Date: 2026-08-06 01:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6d8b56c8a6cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # Escalation Policies
    # ---------------------------------------------------------
    op.create_table(
        "escalation_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("levels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("name", name="uq_escalation_policies_name"),
    )

    # ---------------------------------------------------------
    # Alert Rules
    # ---------------------------------------------------------
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),

        # Matching criteria
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("check_type", sa.String(length=100), nullable=True),
        sa.Column("target", sa.String(length=255), nullable=True),
        sa.Column("metric_name", sa.String(length=100), nullable=True),

        # Thresholds
        sa.Column("warning_threshold", sa.Float(), nullable=True),
        sa.Column("critical_threshold", sa.Float(), nullable=True),

        # Anomaly detection
        sa.Column("anomaly_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("anomaly_tolerance", sa.Float(), nullable=True),

        # State change detection
        sa.Column("state_change_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),

        # Suppression
        sa.Column("ai_suppression_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("maintenance_window_name", sa.String(length=255), nullable=True),

        # Escalation
        sa.Column(
            "escalation_policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("escalation_policies.id", ondelete="SET NULL"),
            nullable=True,
        ),

        # Control
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),

        # Metadata
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.UniqueConstraint("name", name="uq_alert_rules_name"),
    )

    # Useful indexes
    op.create_index("ix_alert_rules_provider", "alert_rules", ["provider"])
    op.create_index("ix_alert_rules_check_type", "alert_rules", ["check_type"])
    op.create_index("ix_alert_rules_enabled", "alert_rules", ["enabled"])
    op.create_index("ix_alert_rules_priority", "alert_rules", ["priority"])
    op.create_index("ix_alert_rules_escalation_policy_id", "alert_rules", ["escalation_policy_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_rules_escalation_policy_id", table_name="alert_rules")
    op.drop_index("ix_alert_rules_priority", table_name="alert_rules")
    op.drop_index("ix_alert_rules_enabled", table_name="alert_rules")
    op.drop_index("ix_alert_rules_check_type", table_name="alert_rules")
    op.drop_index("ix_alert_rules_provider", table_name="alert_rules")

    op.drop_table("alert_rules")
    op.drop_table("escalation_policies")
