from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.itsm import ServiceTicket
from app.models.itsm_extended import ITSMTicketAttachment
from app.schemas.itsm_operational import AttachmentUploadResponse, SLAEscalationResponse, TicketAssignmentRequest, TicketAssignmentResponse
from app.services.itsm_operational_service import ITSMOperationalService
from app.services.itsm_service import ITSMService

router = APIRouter(prefix="/itsm", tags=["ITSM Operations"])


def tenant_id(user):
    return getattr(user, "tenant_id", None)


def ticket_or_404(db: Session, ticket_id: UUID, user) -> ServiceTicket:
    ticket = ITSMService(db).get_ticket(ticket_id, tenant_id=tenant_id(user))
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.post("/tickets/{ticket_id}/assign", response_model=TicketAssignmentResponse)
def assign_ticket(ticket_id: UUID, payload: TicketAssignmentRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = ticket_or_404(db, ticket_id, user)
    try:
        return ITSMOperationalService(db).assign_ticket(ticket, payload.technician_id, payload.assignment_group_id, getattr(user, "email", None) or str(user.id))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/tickets/{ticket_id}/assignments", response_model=list[TicketAssignmentResponse])
def list_assignments(ticket_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket_or_404(db, ticket_id, user)
    return ITSMOperationalService(db).assignments(ticket_id, tenant_id(user))


@router.get("/tickets/{ticket_id}/sla-escalations", response_model=list[SLAEscalationResponse])
def list_sla_escalations(ticket_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket_or_404(db, ticket_id, user)
    from app.models.itsm_operational import ITSMSLAEscalation
    q = db.query(ITSMSLAEscalation).filter(ITSMSLAEscalation.ticket_id == ticket_id)
    if tenant_id(user) is not None:
        q = q.filter(ITSMSLAEscalation.tenant_id == tenant_id(user))
    return q.order_by(ITSMSLAEscalation.created_at.desc()).all()


@router.post("/sla/escalate", response_model=list[SLAEscalationResponse])
def run_sla_escalation(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return ITSMOperationalService(db).escalate_sla(tenant_id(user))


@router.post("/tickets/{ticket_id}/attachment-files", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(ticket_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = ticket_or_404(db, ticket_id, user)
    data = await file.read()
    try:
        row = ITSMOperationalService(db).save_attachment(ticket, file.filename or "attachment", file.content_type, data, getattr(user, "email", None) or str(user.id))
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    return AttachmentUploadResponse.model_validate({"id": row.id, "ticket_id": row.ticket_id, "tenant_id": row.tenant_id, "filename": row.filename, "content_type": row.content_type, "size_bytes": row.size_bytes, "uploaded_by": row.uploaded_by, "created_at": row.created_at, "download_url": f"/api/v1/itsm/tickets/{ticket.id}/attachment-files/{row.id}"})


@router.get("/tickets/{ticket_id}/attachment-files", response_model=list[AttachmentUploadResponse])
def list_attachments(ticket_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = ticket_or_404(db, ticket_id, user)
    q = db.query(ITSMTicketAttachment).filter(ITSMTicketAttachment.ticket_id == ticket.id)
    if tenant_id(user) is not None:
        q = q.filter(ITSMTicketAttachment.tenant_id == tenant_id(user))
    rows = q.order_by(ITSMTicketAttachment.created_at.asc()).all()
    return [AttachmentUploadResponse.model_validate({"id": r.id, "ticket_id": r.ticket_id, "tenant_id": r.tenant_id, "filename": r.filename, "content_type": r.content_type, "size_bytes": r.size_bytes, "uploaded_by": r.uploaded_by, "created_at": r.created_at, "download_url": f"/api/v1/itsm/tickets/{ticket_id}/attachment-files/{r.id}"}) for r in rows]


@router.get("/tickets/{ticket_id}/attachment-files/{attachment_id}")
def download_attachment(ticket_id: UUID, attachment_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = ticket_or_404(db, ticket_id, user)
    row = db.query(ITSMTicketAttachment).filter(ITSMTicketAttachment.id == attachment_id, ITSMTicketAttachment.ticket_id == ticket.id, ITSMTicketAttachment.tenant_id == ticket.tenant_id).first()
    if not row:
        raise HTTPException(404, "Attachment not found")
    try:
        path = ITSMOperationalService(db).attachment_path(row)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Attachment content not found") from exc
    return FileResponse(path, media_type=row.content_type or "application/octet-stream", filename=row.filename)


@router.post("/alerts/{alert_id}/sync-ticket", response_model=dict)
def sync_alert_ticket(alert_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        ticket = ITSMOperationalService(db).sync_alert(alert_id, tenant_id(user))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ticket_id": str(ticket.id), "ticket_number": ticket.number, "alert_id": str(alert_id)}


@router.post("/incidents/{incident_id}/sync-ticket", response_model=dict)
def sync_incident_ticket(incident_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        ticket = ITSMOperationalService(db).sync_incident(incident_id, tenant_id(user))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ticket_id": str(ticket.id), "ticket_number": ticket.number, "incident_id": incident_id, "status": ticket.status}
