"""add_itsm_tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-06 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("number", sa.String(64), nullable=False),
        sa.Column("ticket_type", sa.String(32), nullable=False, server_default="incident"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("impact", sa.String(32), nullable=True),
        sa.Column("urgency", sa.String(32), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("subcategory", sa.String(128), nullable=True),
        sa.Column("requester", sa.String(255), nullable=True),
        sa.Column("assignee", sa.String(255), nullable=True),
        sa.Column("assignment_group", sa.String(128), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("incident_id", sa.String(36), nullable=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_response_minutes", sa.Integer(), nullable=True),
        sa.Column("sla_resolve_minutes", sa.Integer(), nullable=True),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("number", name="uq_service_tickets_number"),
    )
    op.create_index("ix_service_tickets_tenant_id", "service_tickets", ["tenant_id"])
    op.create_index("ix_service_tickets_status", "service_tickets", ["status"])
    op.create_index("ix_service_tickets_priority", "service_tickets", ["priority"])
    op.create_index("ix_service_tickets_ticket_type", "service_tickets", ["ticket_type"])
    op.create_index("ix_service_tickets_number", "service_tickets", ["number"])
    op.create_index("ix_service_tickets_device_id", "service_tickets", ["device_id"])
    op.create_index("ix_service_tickets_incident_id", "service_tickets", ["incident_id"])

    op.create_table(
        "ticket_asset_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="primary"),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_ticket_asset_links_ticket_id", "ticket_asset_links", ["ticket_id"])
    op.create_index("ix_ticket_asset_links_asset_id", "ticket_asset_links", ["asset_id"])
    op.create_index("uq_ticket_asset_link", "ticket_asset_links", ["ticket_id", "asset_id"], unique=True)

    op.create_table(
        "ticket_work_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ticket_work_notes_ticket_id", "ticket_work_notes", ["ticket_id"])


def downgrade() -> None:
    op.drop_table("ticket_work_notes")
    op.drop_table("ticket_asset_links")
    op.drop_table("service_tickets")
