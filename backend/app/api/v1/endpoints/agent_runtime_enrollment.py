from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.endpoints.agent_runtime import (
    EnrollRequest,
    EnrollResponse,
    _agents,
    _commands,
    _persist_agents,
    _platform_metadata,
)
from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.models.device import Device
from app.services.agent_enrollment_service import AgentEnrollmentService
from app.services.entitlement_service import EntitlementService
from app.state import device_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime", tags=["agent-runtime-enrollment"])


@router.post("/enrollment-token")
def create_enrollment_token(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user has no tenant context",
        )

    EntitlementService(db).require_download_allowed(tenant_id, user=user)

    try:
        raw, _record = AgentEnrollmentService(db).create(tenant_id)
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Enrollment-token integrity failure for tenant=%s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "enrollment_token_schema_unavailable",
                "message": "Enrollment-token storage is not ready. Apply the production database migration.",
            },
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Enrollment-token database failure for tenant=%s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "enrollment_token_database_error",
                "message": "Unable to persist the enrollment token.",
            },
        ) from exc

    return {
        "token": raw,
        "expires_at": None,
        "tenant_id": str(tenant_id),
        "single_use": False,
        "reusable": True,
        "revocable": True,
    }


def _upsert_portal_device(db: Session, *, agent_id: uuid.UUID, tenant_id: uuid.UUID, hostname: str, platform: str | None) -> None:
    """Ensure a Device row exists so every portal path can see the endpoint."""
    now = datetime.now(timezone.utc)
    device = db.get(Device, agent_id)
    if device is None:
        # Prefer same id as agent for simple joins in the UI.
        device = Device(
            id=agent_id,
            hostname=hostname or "unknown",
            status="online",
            last_seen=now,
            tenant_id=tenant_id,
        )
        # Some schemas use different column names — set optionally.
        if hasattr(device, "agent_version"):
            pass
        db.add(device)
    else:
        device.hostname = hostname or device.hostname
        device.status = "online"
        device.last_seen = now
        if getattr(device, "tenant_id", None) is None:
            device.tenant_id = tenant_id
    db.commit()


@router.post("/enroll", response_model=EnrollResponse)
def secure_enroll(req: EnrollRequest, db: Session = Depends(get_db)):
    service = AgentEnrollmentService(db)
    try:
        row, agent_token, tenant_id = service.enroll_agent(
            enrollment_secret=req.enrollment_secret or "",
            hostname=req.hostname,
            agent_version=req.agent_version,
            platform=req.platform,
            machine_guid=getattr(req, "machine_guid", None),
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Enrollment integrity failure")
        raise HTTPException(status_code=409, detail="Machine enrollment conflicts with an existing agent") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Enrollment database failure")
        raise HTTPException(status_code=503, detail="Agent enrollment database transaction failed") from exc

    agent_id = str(row.id)
    now = row.last_seen
    registered_at = row.registered_at
    _agents[agent_id] = {
        "agent_id": agent_id,
        "agent_token": agent_token,
        "tenant_id": str(tenant_id),
        "hostname": row.hostname,
        "agent_version": row.agent_version,
        "platform": row.platform,
        "platform_metadata": _platform_metadata(row.platform),
        "status": "online",
        "registered_at": registered_at.isoformat() if registered_at else (now.isoformat() if now else None),
        "last_seen": now.isoformat() if now else datetime.now(timezone.utc).isoformat(),
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "ip_address": None,
        "enrollment_secret": None,
        "commands_completed": 0,
        "commands_failed": 0,
        "enabled": True,
    }
    _commands.setdefault(agent_id, [])

    # Critical: tenant_id must be present or the portal filters the device out.
    device_state.register_device(
        agent_id,
        tenant_id=str(tenant_id),
        hostname=row.hostname,
    )
    _persist_agents()

    try:
        _upsert_portal_device(
            db,
            agent_id=row.id,
            tenant_id=tenant_id,
            hostname=row.hostname or "unknown",
            platform=row.platform,
        )
    except Exception:
        logger.exception("Failed to upsert portal Device row for agent=%s", agent_id)
        db.rollback()

    return EnrollResponse(agent_id=agent_id, agent_token=agent_token)
