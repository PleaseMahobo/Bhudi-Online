"""Phase 14B ITSM SLA, assignment, history and attachments."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("itsm_sla_policies",
        sa.Column("id", uuid, primary_key=True), sa.Column("tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=False), sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("response_minutes", sa.Integer(), nullable=False), sa.Column("resolve_minutes", sa.Integer(), nullable=False),
        sa.Column("business_hours_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_itsm_sla_policies_tenant_id", "itsm_sla_policies", ["tenant_id"])
    op.create_table("itsm_assignment_groups",
        sa.Column("id", uuid, primary_key=True), sa.Column("tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(128), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("escalation_policy_id", uuid, sa.ForeignKey("escalation_policies.id", ondelete="SET NULL")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_itsm_assignment_groups_tenant_id", "itsm_assignment_groups", ["tenant_id"])
    op.create_table("itsm_ticket_history",
        sa.Column("id", uuid, primary_key=True), sa.Column("ticket_id", uuid, sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE")), sa.Column("actor", sa.String(255)),
        sa.Column("action", sa.String(64), nullable=False), sa.Column("field", sa.String(128)), sa.Column("old_value", sa.Text()), sa.Column("new_value", sa.Text()),
        sa.Column("metadata", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_itsm_ticket_history_ticket_id", "itsm_ticket_history", ["ticket_id"])
    op.create_table("itsm_ticket_attachments",
        sa.Column("id", uuid, primary_key=True), sa.Column("ticket_id", uuid, sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE")), sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255)), sa.Column("storage_key", sa.String(1024), nullable=False), sa.Column("size_bytes", sa.Integer()),
        sa.Column("uploaded_by", sa.String(255)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_itsm_ticket_attachments_ticket_id", "itsm_ticket_attachments", ["ticket_id"])


def downgrade() -> None:
    op.drop_table("itsm_ticket_attachments")
    op.drop_table("itsm_ticket_history")
    op.drop_table("itsm_assignment_groups")
    op.drop_table("itsm_sla_policies")
