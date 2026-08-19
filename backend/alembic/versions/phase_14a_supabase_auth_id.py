"""add Supabase auth identity mapping

Revision ID: phase_14a_supabase_auth_id
Revises: abcd1234
"""
from alembic import op
import sqlalchemy as sa

revision = "phase_14a_supabase_auth_id"
down_revision = "abcd1234"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("supabase_auth_id", sa.Uuid(), nullable=True))
    op.create_index("ix_users_supabase_auth_id", "users", ["supabase_auth_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_supabase_auth_id", table_name="users")
    op.drop_column("users", "supabase_auth_id")
