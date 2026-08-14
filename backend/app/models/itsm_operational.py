from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ITSMTicketAssignment(Base):
    __tablename__ = "itsm_ticket_assignments"
    __table_args__ = (
        Index("ix_itsm_ticket_assignments_ticket_id", "ticket_id"),
        Index("ix_itsm_ticket_assignments_technician_id", "technician_id"),
        Index("ix_itsm_ticket_assignments_tenant_id", "tenant_id"),
        UniqueConstraint("ticket_id", "technician_id", name="uq_itsm_ticket_assignment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False)
    technician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("technicians.id", ondelete="CASCADE"), nullable=False)
    assignment_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("itsm_assignment_groups.id", ondelete="SET NULL"), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    assigned_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=_utcnow, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class ITSMSLAEscalation(Base):
    __tablename__ = "itsm_sla_escalations"
    __table_args__ = (
        Index("ix_itsm_sla_escalations_ticket_id", "ticket_id"),
        Index("ix_itsm_sla_escalations_tenant_id", "tenant_id"),
        UniqueConstraint("ticket_id", "breach_type", "level", name="uq_itsm_sla_escalation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    breach_type: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recipient: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=_utcnow, nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
