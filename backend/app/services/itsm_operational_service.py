from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.incident import Incident
from app.models.itsm import ServiceTicket, TicketWorkNote
from app.models.itsm_extended import ITSMAssignmentGroup, ITSMTicketHistory, ITSMTicketAttachment
from app.models.itsm_operational import ITSMTicketAssignment, ITSMSLAEscalation
from app.models.msp import Technician
from app.services.email_service import EmailService


class ITSMOperationalService:
    MAX_ATTACHMENT_BYTES = int(os.getenv("ITSM_MAX_ATTACHMENT_BYTES", str(25 * 1024 * 1024)))
    _SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def assign_ticket(self, ticket: ServiceTicket, technician_id: UUID, group_id: UUID | None, actor: str | None) -> ITSMTicketAssignment:
        technician = self.db.query(Technician).filter(Technician.id == technician_id, Technician.tenant_id == ticket.tenant_id, Technician.status == "active").first()
        if not technician:
            raise ValueError("Active technician not found")
        if group_id is not None:
            group = self.db.query(ITSMAssignmentGroup).filter(ITSMAssignmentGroup.id == group_id, ITSMAssignmentGroup.tenant_id == ticket.tenant_id, ITSMAssignmentGroup.enabled.is_(True)).first()
            if not group:
                raise ValueError("Assignment group not found")
        active = self.db.query(ITSMTicketAssignment).filter(ITSMTicketAssignment.ticket_id == ticket.id, ITSMTicketAssignment.active.is_(True)).all()
        now = self._now()
        for row in active:
            row.active = False
            row.unassigned_at = now
        row = self.db.query(ITSMTicketAssignment).filter(ITSMTicketAssignment.ticket_id == ticket.id, ITSMTicketAssignment.technician_id == technician_id).first()
        if row:
            row.active = True
            row.assignment_group_id = group_id
            row.assigned_by = actor
            row.assigned_at = now
            row.unassigned_at = None
        else:
            row = ITSMTicketAssignment(ticket_id=ticket.id, technician_id=technician_id, assignment_group_id=group_id, tenant_id=ticket.tenant_id, assigned_by=actor, active=True, assigned_at=now)
            self.db.add(row)
        ticket.assignee = getattr(technician, "email", None) or getattr(technician, "display_name", None)
        if group_id:
            group = self.db.get(ITSMAssignmentGroup, group_id)
            ticket.assignment_group = group.name if group else ticket.assignment_group
        self.db.add(TicketWorkNote(ticket_id=ticket.id, author=actor or "system", body=f"Assigned to {getattr(technician, 'display_name', technician_id)}", is_public=False))
        self.db.add(ITSMTicketHistory(ticket_id=ticket.id, tenant_id=ticket.tenant_id, actor=actor, action="assigned", field="assignee", old_value=None, new_value=str(technician_id), metadata_json={"assignment_group_id": str(group_id) if group_id else None}))
        self.db.commit()
        self.db.refresh(row)
        return row

    def assignments(self, ticket_id: UUID, tenant_id: UUID | None):
        q = self.db.query(ITSMTicketAssignment).filter(ITSMTicketAssignment.ticket_id == ticket_id)
        if tenant_id is not None:
            q = q.filter(ITSMTicketAssignment.tenant_id == tenant_id)
        return q.order_by(ITSMTicketAssignment.assigned_at.desc()).all()

    def _attachment_root(self) -> Path:
        root = Path(os.getenv("ITSM_ATTACHMENT_ROOT", "/data/bhudi/attachments")).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def save_attachment(self, ticket: ServiceTicket, filename: str, content_type: str | None, data: bytes, actor: str | None) -> ITSMTicketAttachment:
        if len(data) > self.MAX_ATTACHMENT_BYTES:
            raise ValueError(f"Attachment exceeds {self.MAX_ATTACHMENT_BYTES} bytes")
        safe = self._SAFE_NAME.sub("_", Path(filename).name).strip("._") or "attachment"
        key = f"{ticket.tenant_id or 'global'}/{ticket.id}/{uuid4()}-{safe}"
        root = self._attachment_root()
        path = (root / key).resolve()
        if root not in path.parents:
            raise ValueError("Invalid attachment path")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        row = ITSMTicketAttachment(ticket_id=ticket.id, tenant_id=ticket.tenant_id, filename=safe, content_type=content_type, storage_key=key, size_bytes=len(data), uploaded_by=actor)
        self.db.add(row)
        self.db.add(ITSMTicketHistory(ticket_id=ticket.id, tenant_id=ticket.tenant_id, actor=actor, action="attachment_added", metadata_json={"filename": safe, "size_bytes": len(data)}))
        self.db.commit()
        self.db.refresh(row)
        return row

    def attachment_path(self, row: ITSMTicketAttachment) -> Path:
        root = self._attachment_root()
        path = (root / row.storage_key).resolve()
        if root not in path.parents or not path.is_file():
            raise FileNotFoundError("Attachment not found")
        return path

    def escalate_sla(self, tenant_id: UUID | None = None) -> list[ITSMSLAEscalation]:
        q = self.db.query(ServiceTicket).filter(ServiceTicket.status.notin_(["resolved", "closed", "cancelled"])).filter(ServiceTicket.sla_resolve_minutes.isnot(None))
        if tenant_id is not None:
            q = q.filter(ServiceTicket.tenant_id == tenant_id)
        now = self._now()
        results: list[ITSMSLAEscalation] = []
        for ticket in q.all():
            elapsed = (now - ticket.created_at).total_seconds() / 60
            breach_type = None
            if ticket.sla_response_minutes and elapsed >= ticket.sla_response_minutes and ticket.status in {"new", "open"}:
                breach_type = "response"
            elif ticket.sla_resolve_minutes and elapsed >= ticket.sla_resolve_minutes:
                breach_type = "resolution"
            if not breach_type:
                continue
            exists = self.db.query(ITSMSLAEscalation).filter(ITSMSLAEscalation.ticket_id == ticket.id, ITSMSLAEscalation.breach_type == breach_type, ITSMSLAEscalation.level == 1).first()
            if exists:
                continue
            recipient = ticket.assignee
            if not recipient:
                assignment = self.db.query(ITSMTicketAssignment).filter(ITSMTicketAssignment.ticket_id == ticket.id, ITSMTicketAssignment.active.is_(True)).first()
                if assignment:
                    tech = self.db.get(Technician, assignment.technician_id)
                    recipient = getattr(tech, "email", None) or getattr(tech, "display_name", None)
            event = ITSMSLAEscalation(ticket_id=ticket.id, tenant_id=ticket.tenant_id, breach_type=breach_type, level=1, recipient=recipient)
            self.db.add(event)
            ticket.sla_breached = True
            self.db.add(TicketWorkNote(ticket_id=ticket.id, author="sla-worker", body=f"{breach_type.title()} SLA breached; escalation level 1 triggered.", is_public=False))
            if recipient and "@" in recipient:
                result = EmailService().send(to=[recipient], subject=f"[Bhudi] SLA breach: {ticket.number}", body_text=f"Ticket {ticket.number} has breached its {breach_type} SLA.\n\nTitle: {ticket.title}\nPriority: {ticket.priority}\nStatus: {ticket.status}")
                event.notification_status = "sent" if result.ok else "failed"
                event.error = result.error
                if result.ok:
                    event.notified_at = now
            else:
                event.notification_status = "recorded"
            self.db.commit()
            self.db.refresh(event)
            results.append(event)
        return results

    def sync_alert(self, alert_id: UUID, tenant_id: UUID | None) -> ServiceTicket:
        alert = self.db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == tenant_id).first()
        if not alert:
            raise ValueError("Alert not found")
        existing = self.db.query(ServiceTicket).filter(ServiceTicket.tenant_id == tenant_id, ServiceTicket.source == "alert", ServiceTicket.source_ref == str(alert.id)).first()
        if existing:
            return existing
        priority = "critical" if str(alert.severity).lower() in {"critical", "high"} else "medium"
        ticket = ServiceTicket(number=f"INC-{self._now().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}", tenant_id=tenant_id, ticket_type="incident", title=f"Alert: {alert.type}", description=alert.message, priority=priority, status="open", requester="alert-engine", source="alert", source_ref=str(alert.id), device_id=alert.device_id, incident_id=str(alert.incident_id) if alert.incident_id else None)
        self.db.add(ticket)
        self.db.flush()
        self.db.add(TicketWorkNote(ticket_id=ticket.id, author="alert-engine", body=f"Created from alert {alert.id}.", is_public=False))
        self.db.add(ITSMTicketHistory(ticket_id=ticket.id, tenant_id=tenant_id, actor="alert-engine", action="alert_linked", metadata_json={"alert_id": str(alert.id)}))
        self.db.commit()
        return ticket

    def sync_incident(self, incident_id: str, tenant_id: UUID | None) -> ServiceTicket:
        incident = self.db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == tenant_id).first()
        if not incident:
            raise ValueError("Incident not found")
        ticket = self.db.query(ServiceTicket).filter(ServiceTicket.tenant_id == tenant_id, ServiceTicket.incident_id == str(incident.id)).first()
        if not ticket:
            ticket = ServiceTicket(number=f"INC-{self._now().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}", tenant_id=tenant_id, ticket_type="incident", title=incident.title, description=incident.summary, priority="critical" if str(incident.severity).lower() in {"critical", "high"} else "high", status="open", requester="soc", source="incident", source_ref=str(incident.id), device_id=incident.device_id, incident_id=str(incident.id))
            self.db.add(ticket)
            self.db.flush()
            self.db.add(TicketWorkNote(ticket_id=ticket.id, author="soc", body=f"Created from SOC incident {incident.id}.", is_public=False))
        else:
            mapped = {"open": "in_progress", "investigating": "in_progress", "resolved": "resolved", "closed": "closed"}.get(str(incident.status).lower())
            if mapped and ticket.status != mapped:
                ticket.status = mapped
                if mapped == "resolved" and ticket.resolved_at is None:
                    ticket.resolved_at = self._now()
                if mapped == "closed" and ticket.closed_at is None:
                    ticket.closed_at = self._now()
                self.db.add(TicketWorkNote(ticket_id=ticket.id, author="soc", body=f"Synchronized from incident status: {incident.status}", is_public=False))
        self.db.commit()
        return ticket
