"""make agent enrollment credentials reusable and non-expiring

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "i3j4k5l6m7n8"
down_revision: Union[str, Sequence[str], None] = "h2i3j4k5l6m7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "agent_enrollment_tokens",
        "expires_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        nullable=True,
    )
    # Existing credentials remain usable; their old expiry timestamps are
    # intentionally cleared so the new credential contract is non-expiring.
    op.execute(sa.text("UPDATE agent_enrollment_tokens SET expires_at = NULL"))


def downgrade() -> None:
    # Reintroducing an expiry requires a policy decision; use a safe 24-hour
    # value for rollback rather than leaving a NOT NULL column with NULL data.
    op.execute(sa.text(
        "UPDATE agent_enrollment_tokens "
        "SET expires_at = COALESCE(created_at + INTERVAL '24 hours', now() + INTERVAL '24 hours') "
        "WHERE expires_at IS NULL"
    ))
    op.alter_column(
        "agent_enrollment_tokens",
        "expires_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        nullable=False,
    )
