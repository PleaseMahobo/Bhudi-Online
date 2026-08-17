"""add customer-scoped agent enrollment tokens

Revision ID: h2i3j4k5l6m7
Revises: h1i2j3k4l5m6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "h2i3j4k5l6m7"
down_revision: Union[str, Sequence[str], None] = "h1i2j3k4l5m6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_enrollment_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("token_hash", name="uq_agent_enrollment_tokens_hash"),
    )
    op.create_index("ix_agent_enrollment_tokens_tenant_id", "agent_enrollment_tokens", ["tenant_id"])
    op.create_index("ix_agent_enrollment_tokens_token_hash", "agent_enrollment_tokens", ["token_hash"])
    op.create_index("ix_agent_enrollment_tokens_agent_id", "agent_enrollment_tokens", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_enrollment_tokens_agent_id", table_name="agent_enrollment_tokens")
    op.drop_index("ix_agent_enrollment_tokens_token_hash", table_name="agent_enrollment_tokens")
    op.drop_index("ix_agent_enrollment_tokens_tenant_id", table_name="agent_enrollment_tokens")
    op.drop_table("agent_enrollment_tokens")
