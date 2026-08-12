"""add user security columns

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-12

Adds columns expected by the User model that may be missing on older DBs:
- password_history
- totp_secret
- mfa_enabled
- passkeys
- sso_provider
- password_changed_at (if missing)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _has_column("users", "password_changed_at"):
        op.add_column(
            "users",
            sa.Column("password_changed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        )
    if not _has_column("users", "password_history"):
        op.add_column(
            "users",
            sa.Column("password_history", sa.JSON(), nullable=True),
        )
    if not _has_column("users", "totp_secret"):
        op.add_column(
            "users",
            sa.Column("totp_secret", sa.String(length=255), nullable=True),
        )
    if not _has_column("users", "mfa_enabled"):
        op.add_column(
            "users",
            sa.Column("mfa_enabled", sa.Boolean(), server_default="false", nullable=False),
        )
    if not _has_column("users", "passkeys"):
        op.add_column(
            "users",
            sa.Column("passkeys", sa.JSON(), nullable=True),
        )
    if not _has_column("users", "sso_provider"):
        op.add_column(
            "users",
            sa.Column("sso_provider", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    for col in (
        "sso_provider",
        "passkeys",
        "mfa_enabled",
        "totp_secret",
        "password_history",
        "password_changed_at",
    ):
        if _has_column("users", col):
            op.drop_column("users", col)
