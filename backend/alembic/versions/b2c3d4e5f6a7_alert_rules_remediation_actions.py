"""add remediation_actions to alert_rules

Revision ID: c4d5e6f7a8b9
Revises: a1b2c3d4e5f6
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS remediation_actions JSON"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE alert_rules DROP COLUMN IF EXISTS remediation_actions")
