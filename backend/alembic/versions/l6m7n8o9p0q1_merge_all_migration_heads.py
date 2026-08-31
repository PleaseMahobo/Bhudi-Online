"""merge all Alembic migration heads

Revision ID: l6m7n8o9p0q1
Revises: 7a1b2c3d4e5f, a3b4c5d6e7f8, c4d5e6f7a8b9, k5l6m7n8o9p0
Create Date: 2026-08-31

This merge revision reconciles all independent migration branches into
one authoritative Alembic head. It intentionally performs no schema changes.
"""

from typing import Sequence, Union

revision: str = "l6m7n8o9p0q1"
down_revision: Union[str, Sequence[str], None] = (
    "7a1b2c3d4e5f",
    "a3b4c5d6e7f8",
    "c4d5e6f7a8b9",
    "k5l6m7n8o9p0",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
