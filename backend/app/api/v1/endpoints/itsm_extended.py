from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.alert import Alert
from app.schemas.itsm import SLAPolicyCreate, SLAPolicyResponse, AssignmentGroupCreate, AssignmentGroupResponse, HistoryResponse, AttachmentCreate, AttachmentResponse, TicketIngest, TicketSummary, ServiceTicketResponse
from app.services.itsm_extended_service import ITSMExtendedService
from app.services.itsm_service import ITSMService
router = APIRouter(prefix="/itsm", tags=["ITSM Extended"])
def tenant(user): return getattr(user, "tenant_id", None)
def require_ticket(db, ticket_id, user):
    ticket = ITSMService(db).get_ticket(ticket_id, tenant_id=tenant(user))
    if not ticket: raise HTTPException(404, "Ticket not found")
    return ticket
@router.get("/summary", response_model=TicketSummary)
def summary(db: Session = Depends(get_db), user=Depends(get_current_user)): return ITSMExtendedService(db).summary(tenant(user))
@router.get("/sla-policies", response_model=list[SLAPolicyResponse])
def list_sla(db: Session = Depends(get_db), user=Depends(get_current_user)): return ITSMExtendedService(db).list_sla_policies(tenant(user))
@router.post("/sla-policies", response_model=SLAPolicyResponse, status_code=201)
def create_sla(payload: SLAPolicyCreate, db: Session = Depends(get_db), user=Depends(get_current_user)): return ITSMExtendedService(db).create_sla_policy(payload, tenant(user))
@router.post("/tickets/{ticket_id}/apply-sla", response_model=ServiceTicketResponse)
def apply_sla(ticket_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = require_ticket(db, ticket_id, user); ITSMExtendedService(db).apply_sla(ticket, tenant(user)); return ITSMService(db).get_ticket(ticket.id, tenant_id=tenant(user))
@router.get("/assignment-groups", response_model=list[AssignmentGroupResponse])
def list_groups(db: Session = Depends(get_db), user=Depends(get_current_user)): return ITSMExtendedService(db).list_groups(tenant(user))
@router.post("/assignment-groups", response_model=AssignmentGroupResponse, status_code=201)
def create_group(payload: AssignmentGroupCreate, db: Session = Depends(get_db), user=Depends(get_current_user)): return ITSMExtendedService(db).create_group(payload, tenant(user))
@router.get("/tickets/{ticket_id}/history", response_model=list[HistoryResponse])
def history(ticket_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_ticket(db, ticket_id, user); return ITSMExtendedService(db).history(ticket_id, tenant(user))
@router.post("/tickets/{ticket_id}/attachments", response_model=AttachmentResponse, status_code=201)
def add_attachment(ticket_id: UUID, payload: AttachmentCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = require_ticket(db, ticket_id, user); return ITSMExtendedService(db).add_attachment(ticket, payload, getattr(user, "email", None) or str(user.id))
@router.get("/tickets/{ticket_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(ticket_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_ticket(db, ticket_id, user); return ITSMExtendedService(db).attachments(ticket_id, tenant(user))
@router.post("/intake", response_model=ServiceTicketResponse, status_code=201)
def intake(payload: TicketIngest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_tenant = tenant(user)
    if user_tenant is not None and payload.tenant_id != user_tenant: raise HTTPException(403, "Tenant mismatch")
    return ServiceTicketResponse.model_validate(ITSMExtendedService(db).ingest(payload, getattr(user, "email", None) or str(user.id)))
@router.post("/alerts/{alert_id}/ticket", response_model=ServiceTicketResponse, status_code=201)
def alert_to_ticket(alert_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == tenant(user)).first()
    if not alert: raise HTTPException(404, "Alert not found")
    existing = db.query(__import__('app.models.itsm', fromlist=['ServiceTicket']).ServiceTicket).filter_by(tenant_id=tenant(user), source="alert", source_ref=str(alert.id)).first()
    if existing: return ServiceTicketResponse.model_validate(existing)
    priority = "critical" if str(alert.severity).lower() in {"critical", "high"} else "medium"
    payload = TicketIngest(title=f"Alert: {alert.type}", description=alert.message, requester="alert-engine", priority=priority, ticket_type="incident", source="alert", source_ref=str(alert.id), tenant_id=tenant(user))
    return ServiceTicketResponse.model_validate(ITSMExtendedService(db).ingest(payload, "alert-engine"))
