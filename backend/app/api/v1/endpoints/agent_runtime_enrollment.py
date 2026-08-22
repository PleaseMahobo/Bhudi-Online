from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
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
async def secure_enroll(req: EnrollRequest, request: Request, db: Session = Depends(get_db)):
    enrollment = AgentEnrollmentService(db).consume(req.enrollment_secret or "")
    payload = await request.json()
    machine_guid = str(payload.get("machine_guid") or "").strip().lower() or None
    now = datetime.now(timezone.utc)

    # Enrollment is idempotent for a physical machine within a tenant. A retry,
    # reinstall, or lost local identity must not manufacture another device.
    existing = None
    if machine_guid:
        existing = (
            db.query(Agent)
            .filter(
                Agent.tenant_id == enrollment.tenant_id,
                Agent.machine_guid == machine_guid,
                Agent.revoked.is_(False),
            )
            .one_or_none()
        )

    if existing is not None:
        agent_id = str(existing.id)
        agent_token = existing.enrollment_token or str(uuid.uuid4())
        existing.hostname = req.hostname
        existing.agent_version = req.agent_version
        existing.platform = req.platform
        existing.machine_guid = machine_guid
        existing.status = "online"
        existing.last_seen = now
        existing.last_heartbeat = now
        existing.enabled = True
        existing.registration_state = "approved"
        existing.approved = True
        existing.trusted = True
        existing.enrollment_token = agent_token
        db.flush()
        AgentEnrollmentService(db).mark_used(enrollment, existing.id)

        _agents[agent_id] = {
            "agent_id": agent_id,
            "agent_token": agent_token,
            "tenant_id": str(enrollment.tenant_id),
            "hostname": req.hostname,
            "agent_version": req.agent_version,
            "platform": req.platform,
            "platform_metadata": _platform_metadata(req.platform),
            "status": "online",
            "registered_at": existing.registered_at.isoformat(),
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
        device_state.devices[agent_id]["hostname"] = req.hostname
        _persist_agents()
        return EnrollResponse(agent_id=agent_id, agent_token=agent_token)

    agent_id = str(uuid.uuid4())
    agent_token = str(uuid.uuid4())

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

    row = Agent(
        id=uuid.UUID(agent_id),
        hostname=req.hostname,
        agent_version=req.agent_version,
        platform=req.platform,
        machine_guid=machine_guid,
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
