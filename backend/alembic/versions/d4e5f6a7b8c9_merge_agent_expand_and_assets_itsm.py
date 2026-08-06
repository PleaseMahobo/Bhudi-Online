"""merge_agent_expand_and_assets_itsm

Revision ID: d4e5f6a7b8c9
Revises: 4fa1923c1c82, c3d4e5f6a7b8
Create Date: 2026-08-06 03:05:00.000000

Merges parallel heads:
  - 4fa1923c1c82  (expand_agent_model)  ← current production DB
  - c3d4e5f6a7b8  (ITSM tables, via device-mgmt → alert → assets)
"""
from typing import Sequence, Union

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = ("4fa1923c1c82", "c3d4e5f6a7b8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pure merge — no schema changes
    pass


def downgrade() -> None:
    pass
