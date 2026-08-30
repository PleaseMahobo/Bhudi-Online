"""Audit trail API — list and record privileged / application events.

OpenAPI tag: **audit**

Permissions
-----------
- ``GET /audit/logs`` requires permission ``audit.read``
- ``POST /audit/logs`` requires any authenticated user

System-generated admin actions (billing force-activate, platform-heal, etc.)
are written via ``app.services.audit_service.record_audit`` and appear in the
same list endpoint.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permission
from app.database.session import get_db
from app.models.audit_trail import AuditTrail
from app.models.user import User
from app.schemas.audit import (
    AuditLogCreateRequest,
    AuditLogCreateResponse,
    AuditLogItem,
    AuditLogListResponse,
)

router = APIRouter(prefix="/audit", tags=["audit"])

# Cross-tenant audit access is reserved for explicitly configured platform
# owners. Tenant roles and permissions never bypass tenant scoping.
PLATFORM_AUDIT_OWNER_EMAILS = frozenset({
    "security@bhudi.online",
    "security@cyberbastion.co.za",
})


def _is_platform_audit_owner(user: User) -> bool:
    return (user.email or "").strip().lower() in PLATFORM_AUDIT_OWNER_EMAILS


def _row_to_item(row: AuditTrail) -> AuditLogItem:
    return AuditLogItem(
        id=str(row.id),
        tenant_id=str(row.tenant_id) if row.tenant_id else None,
        user_id=str(row.user_id) if row.user_id else None,
        action=row.action,
        resource=row.resource,
        details=row.details,
        created_at=row.created_at,
    )


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="List audit log entries",
    response_description="Newest audit entries first",
    responses={
        200: {"description": "Audit log page returned"},
        401: {"description": "Missing or invalid authentication"},
        403: {"description": "Caller lacks audit.read permission"},
        503: {"description": "Database unavailable"},
    },
)
def list_audit_logs(
    current_user: User = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of entries to return (1–200)",
    ),
    since: datetime | None = Query(
        default=None,
        description="Only return entries created at or after this UTC timestamp (ISO-8601)",
        examples=["2026-08-01T00:00:00Z"],
    ),
    action: str | None = Query(
        default=None,
        description="Optional exact action filter, e.g. billing.admin.force_activate",
    ),
    resource: str | None = Query(
        default=None,
        description="Optional resource prefix/exact filter, e.g. tenant:<uuid>",
    ),
):
    """Return recent audit trail rows for operators with ``audit.read``.

    Entries include both client-posted events and system-generated admin
    actions (platform heal, billing force-activate, plan seed, inspect).
    """
    try:
        query = db.query(AuditTrail)

        # Tenant isolation is the default. A platform-global principal is the
        # only caller allowed to inspect audit rows across tenant boundaries.
        if not _is_platform_audit_owner(current_user):
            query = query.filter(AuditTrail.tenant_id == current_user.tenant_id)

        query = query.order_by(AuditTrail.created_at.desc())

        if since is not None:
            query = query.filter(AuditTrail.created_at >= since)
        if action:
            query = query.filter(AuditTrail.action == action)
        if resource:
            query = query.filter(AuditTrail.resource == resource)

        rows = query.limit(limit).all()
        return AuditLogListResponse(items=[_row_to_item(r) for r in rows])
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logs unavailable: database connection failed",
        ) from exc


@router.post(
    "/logs",
    response_model=AuditLogCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an audit log entry",
    response_description="Created audit entry id",
    responses={
        201: {"description": "Entry recorded"},
        401: {"description": "Missing or invalid authentication"},
        503: {"description": "Database unavailable"},
    },
)
def create_audit_log(
    body: AuditLogCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Append a client-side audit event for the authenticated user.

    ``tenant_id`` and ``user_id`` are taken from the current session — clients
    cannot impersonate another actor via this endpoint.
    """
    try:
        entry = AuditTrail(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action=body.action,
            resource=body.resource,
            details=body.details or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return AuditLogCreateResponse(status="recorded", id=str(entry.id))
    except SQLAlchemyError as exp:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logs unavailable: database connection failed",
        ) from exp
