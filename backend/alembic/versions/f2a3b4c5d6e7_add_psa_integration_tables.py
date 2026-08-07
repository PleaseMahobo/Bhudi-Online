"""add_psa_integration_tables

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-07 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "psa_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("last_sync_status", sa.String(32), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_psa_connections_tenant_id", "psa_connections", ["tenant_id"])
    op.create_index("ix_psa_connections_provider_key", "psa_connections", ["provider_key"])
    op.create_index("ix_psa_connections_enabled", "psa_connections", ["enabled"])
    op.create_index(
        "uq_psa_connection_tenant_provider",
        "psa_connections",
        ["tenant_id", "provider_key"],
        unique=True,
    )

    op.create_table(
        "psa_ticket_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("psa_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("external_key", sa.String(255), nullable=True),
        sa.Column("external_url", sa.String(1024), nullable=True),
        sa.Column("external_status", sa.String(64), nullable=True),
        sa.Column("direction", sa.String(32), nullable=False, server_default="outbound"),
        sa.Column("sync_status", sa.String(32), nullable=False, server_default="linked"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_psa_ticket_links_connection_id", "psa_ticket_links", ["connection_id"])
    op.create_index("ix_psa_ticket_links_ticket_id", "psa_ticket_links", ["ticket_id"])
    op.create_index("ix_psa_ticket_links_external_id", "psa_ticket_links", ["external_id"])
    op.create_index(
        "uq_psa_ticket_link_connection_ticket",
        "psa_ticket_links",
        ["connection_id", "ticket_id"],
        unique=True,
    )
    op.create_index(
        "uq_psa_ticket_link_connection_external",
        "psa_ticket_links",
        ["connection_id", "external_id"],
        unique=True,
    )

    op.create_table(
        "psa_sync_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("psa_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False, server_default="inbound"),
        sa.Column("external_event_id", sa.String(255), nullable=True),
        sa.Column("external_ticket_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("action", sa.String(512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_psa_sync_events_connection_id", "psa_sync_events", ["connection_id"])
    op.create_index("ix_psa_sync_events_event_type", "psa_sync_events", ["event_type"])
    op.create_index("ix_psa_sync_events_status", "psa_sync_events", ["status"])
    op.create_index("ix_psa_sync_events_external_event_id", "psa_sync_events", ["external_event_id"])
    op.create_index(
        "uq_psa_sync_events_connection_external",
        "psa_sync_events",
        ["connection_id", "external_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("psa_sync_events")
    op.drop_table("psa_ticket_links")
    op.drop_table("psa_connections")
