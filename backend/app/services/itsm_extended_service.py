from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.itsm import ServiceTicket, TicketWorkNote
from app.models.itsm_extended import ITSMSLAPolicy, ITSMAssignmentGroup, ITSMTicketAttachment, ITSMTicketHistory
from app.schemas.itsm import AssignmentGroupCreate, AttachmentCreate, SLAPolicyCreate, TicketIngest


class ITSMExtendedService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _tenant(self, tenant_id: UUID | None):
        return tenant_id

    def list_sla_policies(self, tenant_id: UUID | None):
        q = self.db.query(ITSMSLAPolicy).filter(ITSMSLAPolicy.enabled.is_(True))
        if tenant_id is not None:
            q = q.filter(ITSMSLAPolicy.tenant_id == tenant_id)
        return q.order_by(ITSMSLAPolicy.priority, ITSMSLAPolicy.name).all()

    def create_sla_policy(self, payload: SLAPolicyCreate, tenant_id: UUID | None):
        row = ITSMSLAPolicy(tenant_id=tenant_id, **payload.model_dump())
        self.db.add(row); self.db.commit(); self.db.refresh(row)
        return row

    def apply_sla(self, ticket: ServiceTicket, tenant_id: UUID | None) -> ServiceTicket:
        if ticket.sla_response_minutes and ticket.sla_resolve_minutes:
            return ticket
        q = self.db.query(ITSMSLAPolicy).filter(ITSMSLAPolicy.enabled.is_(True), ITSMSLAPolicy.priority == ticket.priority)
        if tenant_id is not None:
            q = q.filter(ITSMSLAPolicy.tenant_id == tenant_id)
        policy = q.order_by(ITSMSLAPolicy.created_at.desc()).first()
        if policy:
            ticket.sla_response_minutes = policy.response_minutes
            ticket.sla_resolve_minutes = policy.resolve_minutes
            self.db.commit()
        return ticket

    def list_groups(self, tenant_id: UUID | None):
        q = self.db.query(ITSMAssignmentGroup).filter(ITSMAssignmentGroup.enabled.is_(True))
        if tenant_id is not None:
            q = q.filter(ITSMAssignmentGroup.tenant_id == tenant_id)
        return q.order_by(ITSMAssignmentGroup.name).all()

    def create_group(self, payload: AssignmentGroupCreate, tenant_id: UUID | None):
        row = ITSMAssignmentGroup(tenant_id=tenant_id, **payload.model_dump())
        self.db.add(row); self.db.commit(); self.db.refresh(row)
        return row

    def record_history(self, ticket: ServiceTicket, action: str, actor: str | None, field: str | None = None, old_value: str | None = None, new_value: str | None = None, metadata: dict | None = None):
        row = ITSMTicketHistory(ticket_id=ticket.id, tenant_id=ticket.tenant_id, actor=actor, action=action, field=field, old_value=old_value, new_value=new_value, metadata_json=metadata)
        self.db.add(row); self.db.commit(); self.db.refresh(row)
        return row

    def history(self, ticket_id: UUID, tenant_id: UUID | None):
        q = self.db.query(ITSMTicketHistory).filter(ITSMTicketHistory.ticket_id == ticket_id)
        if tenant_id is not None:
            q = q.filter(ITSMTicketHistory.tenant_id == tenant_id)
        return q.order_by(ITSMTicketHistory.created_at.asc()).all()

    def add_attachment(self, ticket: ServiceTicket, payload: AttachmentCreate, actor: str | None):
        row = ITSMTicketAttachment(ticket_id=ticket.id, tenant_id=ticket.tenant_id, uploaded_by=actor, **payload.model_dump())
        self.db.add(row); self.db.commit(); self.db.refresh(row)
        self.record_history(ticket, "attachment_added", actor, metadata={"filename": payload.filename})
        return row

    def attachments(self, ticket_id: UUID, tenant_id: UUID | None):
        q = self.db.query(ITSMTicketAttachment).filter(ITSMTicketAttachment.ticket_id == ticket_id)
        if tenant_id is not None:
            q = q.filter(ITSMTicketAttachment.tenant_id == tenant_id)
        return q.order_by(ITSMTicketAttachment.created_at.asc()).all()

    def summary(self, tenant_id: UUID | None) -> dict:
        q = self.db.query(ServiceTicket)
        if tenant_id is not None:
            q = q.filter(ServiceTicket.tenant_id == tenant_id)
        rows = q.all()
        return {
            "total": len(rows),
            "open": sum(t.status in {"new", "open"} for t in rows),
            "in_progress": sum(t.status == "in_progress" for t in rows),
            "on_hold": sum(t.status == "on_hold" for t in rows),
            "resolved": sum(t.status == "resolved" for t in rows),
            "closed": sum(t.status == "closed" for t in rows),
            "critical": sum(t.priority == "critical" and t.status not in {"resolved", "closed", "cancelled"} for t in rows),
            "sla_breached": sum(bool(t.sla_breached) for t in rows),
        }

    def ingest(self, payload: TicketIngest, actor: str | None):
        from app.schemas.itsm import ServiceTicketCreate
        from app.services.itsm_service import ITSMService
        create = ServiceTicketCreate(title=payload.title, description=payload.description, requester=payload.requester, priority=payload.priority, ticket_type=payload.ticket_type, source=payload.source, source_ref=payload.source_ref, tenant_id=payload.tenant_id)
        ticket = ITSMService(self.db).create_ticket(create)
        self.apply_sla(ticket, payload.tenant_id)
        self.record_history(ticket, "ingested", actor, metadata={"source": payload.source, "source_ref": payload.source_ref})
        return ticket
