from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.services.agent_enrollment_service import AgentEnrollmentService
from app.state import device_state
from app.api.v1.endpoints.agent_runtime import (
    EnrollRequest,
    EnrollResponse,
    _agents,
    _commands,
    _persist_agents,
    _platform_metadata,
)

router = APIRouter(prefix="/runtime", tags=["agent-runtime-enrollment"])


@router.post("/enrollment-token")
def create_enrollment_token(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    raw, record = AgentEnrollmentService(db).create(user.tenant_id)
    return {
        "token": raw,
        "expires_at": None,
        "tenant_id": str(user.tenant_id),
        "single_use": False,
        "reusable": True,
        "revocable": True,
    }


@router.post("/enroll", response_model=EnrollResponse)
def secure_enroll(req: EnrollRequest, db: Session = Depends(get_db)):
    service = AgentEnrollmentService(db)
    try:
        row, agent_token, tenant_id = service.enroll_agent(
            enrollment_secret=req.enrollment_secret or "",
            hostname=req.hostname,
            agent_version=req.agent_version,
            platform=req.platform,
            machine_guid=req.machine_guid,
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        print(f"[runtime] enrollment integrity failure: {exc}")
        raise HTTPException(status_code=409, detail="Machine enrollment conflicts with an existing agent") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"[runtime] enrollment database failure: {exc}")
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
        "registered_at": registered_at.isoformat() if registered_at else now.isoformat(),
        "last_seen": now.isoformat(),
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "ip_address": None,
        "enrollment_secret": None,
        "commands_completed": 0,
        "commands_failed": 0,
    }
    _commands.setdefault(agent_id, [])
    device_state.register_device(agent_id)
    device_state.devices[agent_id]["hostname"] = row.hostname
    _persist_agents()
    return EnrollResponse(agent_id=agent_id, agent_token=agent_token)
