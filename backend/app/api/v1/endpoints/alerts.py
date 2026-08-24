from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import require_tenant_user
from app.core.ws_manager import manager
from app.database.session import get_db
from app.models.alert import Alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertResponse(BaseModel):
    id: UUID
    device_id: UUID | None
    tenant_id: UUID | None
    type: str
    severity: str
    message: str
    resolved: bool
    status: str
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    resolved_by: str | None
    resolved_at: datetime | None
    threat_score: int | None
    mitre_id: str | None
    mitre_name: str | None
    incident_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


def _tenant_alert(db: Session, alert_id: UUID, tenant_id):
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == tenant_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


def _event(alert: Alert, action: str) -> dict:
    return {"type": "alert.updated", "action": action, "data": {"id": str(alert.id), "tenant_id": str(alert.tenant_id), "status": alert.status, "resolved": alert.resolved}}


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_tenant_user),
    db: Session = Depends(get_db),
):
    query = db.query(Alert).filter(Alert.tenant_id == current_user.tenant_id)
    if status_filter:
        query = query.filter(Alert.status == status_filter)
    if severity:
        query = query.filter(Alert.severity == severity)
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: UUID, current_user=Depends(require_tenant_user), db: Session = Depends(get_db)):
    alert = _tenant_alert(db, alert_id, current_user.tenant_id)
    if alert.status == "resolved":
        raise HTTPException(status_code=409, detail="Resolved alert cannot be acknowledged")
    alert.status = "acknowledged"
    alert.acknowledged_by = str(current_user.id)
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    await manager.broadcast(_event(alert, "acknowledged"), channel="alerts", tenant_id=str(current_user.tenant_id))
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(alert_id: UUID, current_user=Depends(require_tenant_user), db: Session = Depends(get_db)):
    alert = _tenant_alert(db, alert_id, current_user.tenant_id)
    if alert.status == "resolved":
        return alert
    alert.status = "resolved"
    alert.resolved = True
    alert.resolved_by = str(current_user.id)
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    await manager.broadcast(_event(alert, "resolved"), channel="alerts", tenant_id=str(current_user.tenant_id))
    return alert
