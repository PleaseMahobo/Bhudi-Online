from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.itsm import ServiceTicket, TicketWorkNote
from app.models.itsm_extended import ITSMTicketHistory


class ITSMIncidentSyncService:
    TICKET_TO_INCIDENT = {
        "open": "open",
        "new": "open",
        "in_progress": "investigating",
        "on_hold": "investigating",
        "resolved": "resolved",
        "closed": "closed",
        "cancelled": "closed",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def ticket_to_incident(self, ticket_id: UUID, tenant_id: UUID | None, actor: str | None) -> Incident:
        ticket = self.db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id, ServiceTicket.tenant_id == tenant_id).first()
        if not ticket or not ticket.incident_id:
            raise ValueError("Ticket or linked incident not found")
        incident = self.db.query(Incident).filter(Incident.id == str(ticket.incident_id), Incident.tenant_id == tenant_id).first()
        if not incident:
            raise ValueError("Linked incident not found")
        mapped = self.TICKET_TO_INCIDENT.get(str(ticket.status).lower())
        if mapped and incident.status != mapped:
            incident.status = mapped
            incident.updated_at = datetime.now(timezone.utc)
            self.db.add(TicketWorkNote(ticket_id=ticket.id, author=actor or "itsm", body=f"Synchronized ticket status {ticket.status} → incident status {mapped}.", is_public=False))
            self.db.add(ITSMTicketHistory(ticket_id=ticket.id, tenant_id=tenant_id, actor=actor, action="incident_status_synced", old_value=None, new_value=mapped, metadata_json={"incident_id": str(incident.id)}))
            self.db.commit()
        return incident
