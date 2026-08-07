from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationDeliveryResponse,
    NotificationSendRequest,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/catalog")
def channel_catalog(db: Session = Depends(get_db)):
    return NotificationService(db).list_catalog()


@router.post("/channels", response_model=NotificationChannelResponse, status_code=201)
def create_channel(payload: NotificationChannelCreate, db: Session = Depends(get_db)):
    try:
        return NotificationService(db).create_channel(payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/channels", response_model=list[NotificationChannelResponse])
def list_channels(
    tenant_id: UUID | None = None,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    return NotificationService(db).list_channels(tenant_id=tenant_id, enabled_only=enabled_only)


@router.patch("/channels/{channel_id}", response_model=NotificationChannelResponse)
def update_channel(
    channel_id: UUID, payload: NotificationChannelUpdate, db: Session = Depends(get_db)
):
    row = NotificationService(db).update_channel(channel_id, payload)
    if not row:
        raise HTTPException(404, "Channel not found")
    return row


@router.delete("/channels/{channel_id}", status_code=204)
def delete_channel(channel_id: UUID, db: Session = Depends(get_db)):
    if not NotificationService(db).delete_channel(channel_id):
        raise HTTPException(404, "Channel not found")


@router.post("/templates", response_model=NotificationTemplateResponse, status_code=201)
def create_template(payload: NotificationTemplateCreate, db: Session = Depends(get_db)):
    return NotificationService(db).create_template(payload)


@router.get("/templates", response_model=list[NotificationTemplateResponse])
def list_templates(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    return NotificationService(db).list_templates(tenant_id=tenant_id)


@router.patch("/templates/{template_id}", response_model=NotificationTemplateResponse)
def update_template(
    template_id: UUID, payload: NotificationTemplateUpdate, db: Session = Depends(get_db)
):
    row = NotificationService(db).update_template(template_id, payload)
    if not row:
        raise HTTPException(404, "Template not found")
    return row


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: UUID, db: Session = Depends(get_db)):
    if not NotificationService(db).delete_template(template_id):
        raise HTTPException(404, "Template not found")


@router.post("/send", response_model=NotificationDeliveryResponse, status_code=201)
def send_notification(payload: NotificationSendRequest, db: Session = Depends(get_db)):
    try:
        return NotificationService(db).send(payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/deliveries", response_model=list[NotificationDeliveryResponse])
def list_deliveries(
    channel_id: UUID | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return NotificationService(db).list_deliveries(
        channel_id=channel_id, status=status_filter, limit=min(limit, 200)
    )
