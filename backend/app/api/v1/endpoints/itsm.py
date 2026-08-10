from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.itsm import (
    AssetTicketCreateRequest,
    ServiceTicketCreate,
    ServiceTicketResponse,
    ServiceTicketUpdate,
    TicketAssetLinkCreate,
    TicketAssetLinkResponse,
    TicketStatusUpdate,
    WorkNoteCreate,
    WorkNoteResponse,
)
from app.services.itsm_service import ITSMService

router = APIRouter(prefix="/itsm", tags=["ITSM"])


def _ticket_response(ticket) -> ServiceTicketResponse:
    links = []
    for link in ticket.asset_links or []:
        links.append(
            TicketAssetLinkResponse(
                id=link.id,
                ticket_id=link.ticket_id,
                asset_id=link.asset_id,
                role=link.role,
                linked_at=link.linked_at,
                notes=link.notes,
                asset_name=getattr(link, "asset_name", None),
                asset_tag=getattr(link, "asset_tag", None),
                asset_status=getattr(link, "asset_status", None),
            )
        )
    base = ServiceTicketResponse.model_validate(ticket)
    base.asset_links = links
    return base


@router.post(
    "/tickets", response_model=ServiceTicketResponse, status_code=status.HTTP_201_CREATED
)
def create_ticket(payload: ServiceTicketCreate, db: Session = Depends(get_db)):
    ticket = ITSMService(db).create_ticket(payload)
    return _ticket_response(ticket)


@router.get("/tickets", response_model=list[ServiceTicketResponse])
def list_tickets(
    status: str | None = None,
    ticket_type: str | None = None,
    asset_id: UUID | None = None,
    device_id: UUID | None = None,
    priority: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    tickets = ITSMService(db).list_tickets(
        status=status,
        ticket_type=ticket_type,
        asset_id=asset_id,
        device_id=device_id,
        priority=priority,
        q=q,
    )
    return [_ticket_response(t) for t in tickets]


@router.get("/tickets/by-number/{number}", response_model=ServiceTicketResponse)
def get_ticket_by_number(number: str, db: Session = Depends(get_db)):
    ticket = ITSMService(db).get_ticket_by_number(number)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return _ticket_response(ticket)


@router.get("/tickets/{ticket_id}", response_model=ServiceTicketResponse)
def get_ticket(ticket_id: UUID, db: Session = Depends(get_db)):
    ticket = ITSMService(db).get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return _ticket_response(ticket)


@router.patch("/tickets/{ticket_id}", response_model=ServiceTicketResponse)
def update_ticket(
    ticket_id: UUID, payload: ServiceTicketUpdate, db: Session = Depends(get_db)
):
    ticket = ITSMService(db).update_ticket(ticket_id, payload)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return _ticket_response(ticket)


@router.post("/tickets/{ticket_id}/status", response_model=ServiceTicketResponse)
def set_ticket_status(
    ticket_id: UUID, payload: TicketStatusUpdate, db: Session = Depends(get_db)
):
    ticket = ITSMService(db).set_status(ticket_id, payload)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return _ticket_response(ticket)


@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: UUID, db: Session = Depends(get_db)):
    if not ITSMService(db).delete_ticket(ticket_id):
        raise HTTPException(404, "Ticket not found")


@router.post(
    "/tickets/{ticket_id}/assets",
    response_model=TicketAssetLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_asset(
    ticket_id: UUID, payload: TicketAssetLinkCreate, db: Session = Depends(get_db)
):
    try:
        link = ITSMService(db).link_asset(ticket_id, payload)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return TicketAssetLinkResponse.model_validate(link)


@router.delete(
    "/tickets/{ticket_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT
)
def unlink_asset(ticket_id: UUID, asset_id: UUID, db: Session = Depends(get_db)):
    if not ITSMService(db).unlink_asset(ticket_id, asset_id):
        raise HTTPException(404, "Link not found")


@router.get(
    "/assets/{asset_id}/tickets", response_model=list[ServiceTicketResponse]
)
def tickets_for_asset(asset_id: UUID, db: Session = Depends(get_db)):
    tickets = ITSMService(db).tickets_for_asset(asset_id)
    return [_ticket_response(t) for t in tickets]


@router.post(
    "/assets/{asset_id}/tickets",
    response_model=ServiceTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_for_asset(
    asset_id: UUID, payload: AssetTicketCreateRequest, db: Session = Depends(get_db)
):
    try:
        ticket = ITSMService(db).create_ticket_for_asset(asset_id, payload)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _ticket_response(ticket)


@router.post(
    "/tickets/{ticket_id}/notes",
    response_model=WorkNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_work_note(
    ticket_id: UUID, payload: WorkNoteCreate, db: Session = Depends(get_db)
):
    try:
        return ITSMService(db).add_work_note(ticket_id, payload)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/tickets/{ticket_id}/notes", response_model=list[WorkNoteResponse])
def list_work_notes(ticket_id: UUID, db: Session = Depends(get_db)):
    return ITSMService(db).list_work_notes(ticket_id)


@router.post(
    "/jobs/warranty-expiry",
    response_model=list[ServiceTicketResponse],
)
def job_warranty_expiry(within_days: int = 30, db: Session = Depends(get_db)):
    tickets = ITSMService(db).open_warranty_expiry_tickets(within_days=within_days)
    return [_ticket_response(t) for t in tickets]
