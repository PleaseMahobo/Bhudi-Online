"""add_stripe_webhook_events_and_price_id

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-07 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "billing_plans",
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_billing_plans_stripe_price_id",
        "billing_plans",
        ["stripe_price_id"],
        unique=False,
    )
    op.create_index(
        "uq_billing_plans_stripe_price_id",
        "billing_plans",
        ["stripe_price_id"],
        unique=True,
        postgresql_where=sa.text("stripe_price_id IS NOT NULL"),
    )

    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stripe_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("livemode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("action", sa.String(512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("stripe_event_id", name="uq_stripe_webhook_events_event_id"),
    )
    op.create_index(
        "ix_stripe_webhook_events_stripe_event_id",
        "stripe_webhook_events",
        ["stripe_event_id"],
    )
    op.create_index(
        "ix_stripe_webhook_events_event_type",
        "stripe_webhook_events",
        ["event_type"],
    )
    op.create_index(
        "ix_stripe_webhook_events_status",
        "stripe_webhook_events",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
    op.drop_index("uq_billing_plans_stripe_price_id", table_name="billing_plans")
    op.drop_index("ix_billing_plans_stripe_price_id", table_name="billing_plans")
    op.drop_column("billing_plans", "stripe_price_id")
