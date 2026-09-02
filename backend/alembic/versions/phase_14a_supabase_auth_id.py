"""add Supabase auth identity mapping

Revision ID: phase_14a_supabase_auth_id
Revises: f7a8b9c0d1e2
"""
from alembic import op
import sqlalchemy as sa

revision = "phase_14a_supabase_auth_id"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("users")}
    if "supabase_auth_id" not in columns:
        op.add_column("users", sa.Column("supabase_auth_id", sa.Uuid(), nullable=True))
    indexes = {idx["name"]: idx for idx in sa.inspect(bind).get_indexes("users")}
    existing_index = indexes.get("ix_users_supabase_auth_id")
    if existing_index is None:
        op.create_index(
            "ix_users_supabase_auth_id",
            "users",
            ["supabase_auth_id"],
            unique=True,
        )
    elif not existing_index.get("unique", False):
        raise RuntimeError(
            "Existing ix_users_supabase_auth_id is not unique; refusing unsafe reconciliation"
        )


def downgrade() -> None:
    op.drop_index("ix_users_supabase_auth_id", table_name="users")
    op.drop_column("users", "supabase_auth_id")
