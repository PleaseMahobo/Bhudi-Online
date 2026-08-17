from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.schemas.agent import (
    AgentApprovalRequest,
    AgentAuthenticationRequest,
    AgentCommandRequest,
    AgentCommandResponse,
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentResponse,
    AgentRevocationRequest,
    AgentUpdateRequest,
)
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["Agents"])


def _tenant_id(user):
    return user.tenant_id


@router.post("/enroll", response_model=AgentEnrollResponse, status_code=status.HTTP_201_CREATED)
def enroll_agent(
    request: AgentEnrollRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    agent = AgentService(db).enroll(
        device_id=request.device_id,
        hostname=request.hostname,
        version=request.agent_version,
        enrollment_secret=request.enrollment_secret,
        tenant_id=_tenant_id(user),
    )
    return AgentEnrollResponse(
        agent_uuid=agent.agent_uuid,
        registration_state=agent.registration_state,
        heartbeat_interval=agent.heartbeat_interval,
        poll_interval=agent.poll_interval,
    )


@router.post("/authenticate", response_model=AgentResponse)
def authenticate_agent(request: AgentAuthenticationRequest, db: Session = Depends(get_db)):
    return AgentService(db).authenticate(
        agent_uuid=request.agent_uuid,
        enrollment_secret=request.enrollment_secret,
    )


@router.post("/{agent_id}/approve", response_model=AgentResponse)
def approve_agent(
    agent_id: UUID,
    request: AgentApprovalRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).approve(agent_id, request.approved_by, _tenant_id(user))


@router.post("/heartbeat", response_model=AgentHeartbeatResponse)
def heartbeat(request: AgentHeartbeatRequest, db: Session = Depends(get_db)):
    agent = AgentService(db).heartbeat(
        agent_uuid=request.agent_uuid,
        ip_address=request.ip_address,
        username=request.username,
    )
    return AgentHeartbeatResponse(
        status="ok",
        server_time=datetime.now(timezone.utc),
        poll_interval=agent.poll_interval,
        heartbeat_interval=agent.heartbeat_interval,
        update_available=agent.update_available,
        target_version=agent.target_version,
    )


@router.post("/{agent_id}/updates", response_model=AgentResponse)
def publish_update(
    agent_id: UUID,
    request: AgentUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).mark_update_available(agent_id, request.target_version, _tenant_id(user))


@router.post("/{agent_id}/commands", response_model=AgentCommandResponse)
def queue_command(
    agent_id: UUID,
    request: AgentCommandRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    # Command queue implementation remains owned by the enterprise dispatcher.
    # Resolve the target through the tenant-scoped service before accepting it.
    AgentService(db)._scoped_agent(agent_id, _tenant_id(user))
    return AgentCommandResponse(
        accepted=True,
        command_id=UUID("00000000-0000-0000-0000-000000000001"),
    )


@router.post("/{agent_id}/quarantine", response_model=AgentResponse)
def quarantine(
    agent_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).quarantine(agent_id, _tenant_id(user))


@router.post("/{agent_id}/restore", response_model=AgentResponse)
def restore(
    agent_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).restore(agent_id, _tenant_id(user))


@router.post("/{agent_id}/revoke", response_model=AgentResponse)
def revoke(
    agent_id: UUID,
    request: AgentRevocationRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).revoke(
        agent_id=agent_id,
        reason=request.reason,
        tenant_id=_tenant_id(user),
    )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).agents.get(agent_id, tenant_id=_tenant_id(user))


@router.get("/pending/list", response_model=list[AgentResponse])
def pending_agents(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).agents.pending_agents(tenant_id=_tenant_id(user))


@router.get("/online/list", response_model=list[AgentResponse])
def online_agents(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).agents.online_agents(tenant_id=_tenant_id(user))


@router.get("/offline/list", response_model=list[AgentResponse])
def offline_agents(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    return AgentService(db).agents.offline_agents(tenant_id=_tenant_id(user))
