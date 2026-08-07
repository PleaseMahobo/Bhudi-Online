from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.psa import (
    PSAConnectionCreate,
    PSAConnectionResponse,
    PSAConnectionTestResult,
    PSAConnectionUpdate,
    PSASyncEventResponse,
    PSATicketLinkResponse,
    PSATicketPushRequest,
    PSAWebhookResult,
)
from app.services.psa_service import PROVIDER_CATALOG, PSAService

router = APIRouter(prefix="/psa", tags=["PSA Integration"])


def _link_resp(row) -> PSATicketLinkResponse:
    data = PSATicketLinkResponse.model_validate(row)
    if getattr(row, "connection", None):
        data.provider_key = row.connection.provider_key
    return data


@router.get("/catalog")
def list_catalog():
    return PROVIDER_CATALOG


@router.post(
    "/connections/seed",
    response_model=list[PSAConnectionResponse],
    status_code=status.HTTP_201_CREATED,
)
def seed_connections(
    tenant_id: UUID | None = None, db: Session = Depends(get_db)
):
    return PSAService(db).seed_connections(tenant_id=tenant_id)


@router.post(
    "/connections",
    response_model=PSAConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_connection(payload: PSAConnectionCreate, db: Session = Depends(get_db)):
    try:
        return PSAService(db).create_connection(payload)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.get("/connections", response_model=list[PSAConnectionResponse])
def list_connections(
    enabled_only: bool = False,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return PSAService(db).list_connections(
        enabled_only=enabled_only, tenant_id=tenant_id
    )


@router.get("/connections/{connection_id}", response_model=PSAConnectionResponse)
def get_connection(connection_id: UUID, db: Session = Depends(get_db)):
    row = PSAService(db).get_connection(connection_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    return row


@router.patch("/connections/{connection_id}", response_model=PSAConnectionResponse)
def update_connection(
    connection_id: UUID,
    payload: PSAConnectionUpdate,
    db: Session = Depends(get_db),
):
    row = PSAService(db).update_connection(connection_id, payload)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    return row


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(connection_id: UUID, db: Session = Depends(get_db)):
    if not PSAService(db).delete_connection(connection_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")


@router.post(
    "/connections/{connection_id}/test", response_model=PSAConnectionTestResult
)
def test_connection(connection_id: UUID, db: Session = Depends(get_db)):
    try:
        return PSAService(db).test_connection(connection_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.post("/tickets/push", response_model=PSATicketLinkResponse, status_code=201)
def push_ticket(payload: PSATicketPushRequest, db: Session = Depends(get_db)):
    try:
        link = PSAService(db).push_ticket(payload)
    except ValueError as e:
        msg = str(e)
        code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(code, msg) from e
    except Exception as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e

    rows = PSAService(db).list_links(connection_id=link.connection_id)
    loaded = next((r for r in rows if r.id == link.id), link)
    return _link_resp(loaded)


@router.get("/links", response_model=list[PSATicketLinkResponse])
def list_links(
    connection_id: UUID | None = None,
    ticket_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    rows = PSAService(db).list_links(
        connection_id=connection_id, ticket_id=ticket_id
    )
    return [_link_resp(r) for r in rows]


@router.get("/events", response_model=list[PSASyncEventResponse])
def list_events(
    connection_id: UUID | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return PSAService(db).list_events(
        connection_id=connection_id, status=status_filter, limit=min(limit, 200)
    )


@router.post(
    "/connections/{connection_id}/webhook",
    response_model=PSAWebhookResult,
)
async def inbound_webhook(
    connection_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_hub_signature_256: str | None = Header(
        default=None, alias="X-Hub-Signature-256"
    ),
):
    raw = await request.body()
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "JSON body required") from None

    signature = x_hub_signature_256 or x_signature
    try:
        result = PSAService(db).process_webhook(
            connection_id,
            payload,
            signature=signature,
            raw_body=raw,
        )
    except ValueError as e:
        msg = str(e)
        if "signature" in msg.lower():
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg) from e
        code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(code, msg) from e
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e)) from e

    return PSAWebhookResult(
        status=result["status"],
        action=result.get("action"),
        event_id=result.get("event_id"),
        duplicate=bool(result.get("duplicate")),
    )
