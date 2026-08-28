from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.access_tiers import require_mfa_for_actions
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.command import CommandCreateRequest
from app.services.agent_dispatcher import AgentDispatcher

router = APIRouter(prefix="/commands", tags=["Commands"])


@router.post("", status_code=status.HTTP_201_CREATED)
def queue_command(
    request: CommandCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_mfa_for_actions),
):
    dispatcher = AgentDispatcher(db)
    try:
        command = dispatcher.queue_command(
            agent_id=request.agent_id,
            command_type=request.command_type,
            payload=request.payload,
            requested_by=request.requested_by or getattr(_user, "id", None),
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            requires_reboot=request.requires_reboot,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"id": command.id, "status": command.status, "agent_id": command.agent_id, "command_type": command.command_type}


@router.get("/{agent_id}")
def list_agent_commands(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    dispatcher = AgentDispatcher(db)
    return dispatcher.get_pending_commands(agent_id)
