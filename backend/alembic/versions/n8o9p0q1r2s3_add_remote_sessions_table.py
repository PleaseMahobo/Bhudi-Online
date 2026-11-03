"""add remote_sessions durable store

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "n8o9p0q1r2s3"
down_revision: Union[str, Sequence[str], None] = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "remote_sessions",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_user_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("session_type", sa.Text(), nullable=False),
        sa.Column("command_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("dashboard_ticket", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("input_ticket", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("agent_ticket", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("transcript", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_remote_sessions_tenant_id", "remote_sessions", ["tenant_id"])
    op.create_index("ix_remote_sessions_agent_id", "remote_sessions", ["agent_id"])
    op.create_index("ix_remote_sessions_status", "remote_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_remote_sessions_status", table_name="remote_sessions")
    op.drop_index("ix_remote_sessions_agent_id", table_name="remote_sessions")
    op.drop_index("ix_remote_sessions_tenant_id", table_name="remote_sessions")
    op.drop_table("remote_sessions")
