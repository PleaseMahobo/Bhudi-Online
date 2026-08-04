from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permission
from app.database.session import get_db
from app.models.user import User
from app.models.audit_trail import AuditTrail

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_audit_logs(
    current_user: User = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    since: datetime | None = None,
):
    try:
        query = db.query(AuditTrail).order_by(AuditTrail.created_at.desc())

        if since is not None:
            query = query.filter(AuditTrail.created_at >= since)

        rows = query.limit(limit).all()
        return {
            "items": [
                {
                    "id": str(row.id),
                    "tenant_id": str(row.tenant_id) if row.tenant_id else None,
                    "user_id": str(row.user_id) if row.user_id else None,
                    "action": row.action,
                    "resource": row.resource,
                    "details": row.details,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logs unavailable: database connection failed",
        ) from exc


@router.post("/logs", status_code=status.HTTP_201_CREATED)
def create_audit_log(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    action: str = "action",
    resource: str | None = None,
    details: dict[str, Any] | None = None,
):
    try:
        entry = AuditTrail(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action=action,
            resource=resource,
            details=details or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return {"status": "recorded", "id": str(entry.id)}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logs unavailable: database connection failed",
        ) from exc
