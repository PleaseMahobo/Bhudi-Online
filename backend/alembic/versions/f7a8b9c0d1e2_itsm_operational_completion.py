"""Phase 14C ITSM technician assignment and SLA escalation."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "itsm_ticket_assignments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("ticket_id", uuid, sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technician_id", uuid, sa.ForeignKey("technicians.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_group_id", uuid, sa.ForeignKey("itsm_assignment_groups.id", ondelete="SET NULL")),
        sa.Column("tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE")),
        sa.Column("assigned_by", sa.String(255)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("unassigned_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("ticket_id", "technician_id", name="uq_itsm_ticket_assignment"),
    )
    op.create_index("ix_itsm_ticket_assignments_ticket_id", "itsm_ticket_assignments", ["ticket_id"])
    op.create_index("ix_itsm_ticket_assignments_technician_id", "itsm_ticket_assignments", ["technician_id"])
    op.create_index("ix_itsm_ticket_assignments_tenant_id", "itsm_ticket_assignments", ["tenant_id"])

    op.create_table(
        "itsm_sla_escalations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("ticket_id", uuid, sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", uuid, sa.ForeignKey("tenants.id", ondelete="CASCADE")),
        sa.Column("breach_type", sa.String(32), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("recipient", sa.String(512)),
        sa.Column("notification_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("ticket_id", "breach_type", "level", name="uq_itsm_sla_escalation"),
    )
    op.create_index("ix_itsm_sla_escalations_ticket_id", "itsm_sla_escalations", ["ticket_id"])
    op.create_index("ix_itsm_sla_escalations_tenant_id", "itsm_sla_escalations", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("itsm_sla_escalations")
    op.drop_table("itsm_ticket_assignments")
