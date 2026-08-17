from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.models.agent import Agent
from app.services.agent_enrollment_service import AgentEnrollmentService
from app.state import device_state
from app.api.v1.endpoints.agent_runtime import EnrollRequest, EnrollResponse, _agents, _commands, _persist_agents, _platform_metadata

router = APIRouter(prefix="/runtime", tags=["agent-runtime-enrollment"])


@router.post("/enrollment-token")
def create_enrollment_token(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    raw, record = AgentEnrollmentService(db).create(user.tenant_id)
    return {
        "token": raw,
        "expires_at": record.expires_at,
        "tenant_id": str(user.tenant_id),
    }


@router.post("/enroll", response_model=EnrollResponse)
def secure_enroll(req: EnrollRequest, db: Session = Depends(get_db)):
    enrollment = AgentEnrollmentService(db).consume(req.enrollment_secret or "")

    agent_id = str(uuid.uuid4())
    agent_token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    _agents[agent_id] = {
        "agent_id": agent_id,
        "agent_token": agent_token,
        "tenant_id": str(enrollment.tenant_id),
        "hostname": req.hostname,
        "agent_version": req.agent_version,
        "platform": req.platform,
        "platform_metadata": _platform_metadata(req.platform),
        "status": "online",
        "registered_at": now.isoformat(),
        "last_seen": now.isoformat(),
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "ip_address": None,
        "enrollment_secret": None,
        "commands_completed": 0,
        "commands_failed": 0,
    }
    _commands[agent_id] = []

    # The enrollment token is the authoritative tenant binding. The agent cannot
    # choose or override this tenant during enrollment.
    row = Agent(
        id=uuid.UUID(agent_id),
        hostname=req.hostname,
        agent_version=req.agent_version,
        platform=req.platform,
        tenant_id=enrollment.tenant_id,
        enrollment_token=agent_token,
        registration_state="approved",
        approved=True,
        trusted=True,
        status="online",
        enabled=True,
        registered_at=now,
        last_seen=now,
        last_heartbeat=now,
    )
    db.add(row)
    db.flush()
    AgentEnrollmentService(db).mark_used(enrollment, uuid.UUID(agent_id))

    device_state.register_device(agent_id)
    device_state.devices[agent_id]["hostname"] = req.hostname
    _persist_agents()
    return EnrollResponse(agent_id=agent_id, agent_token=agent_token)
