"""add missing agent-to-device relationship column

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "j4k5l6m7n8o9"
down_revision: Union[str, Sequence[str], None] = "i3j4k5l6m7n8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_agents_device_id",
        "agents",
        ["device_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_agents_device_id", table_name="agents")
    op.drop_column("agents", "device_id")
