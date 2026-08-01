from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.command import CommandCreateRequest
from app.services.agent_dispatcher import AgentDispatcher

router = APIRouter(
    prefix="/commands",
    tags=["Commands"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def queue_command(
    request: CommandCreateRequest,
    db: Session = Depends(get_db),
):

    dispatcher = AgentDispatcher(db)

    try:

        command = dispatcher.queue_command(

            agent_id=request.agent_id,

            command_type=request.command_type,

            payload=request.payload,

            priority=request.priority,

            requested_by=request.requested_by,

        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return {

        "id": command.id,

        "status": "queued",

        "agent_id": command.agent_id,

    }


@router.get("/{agent_id}")
def list_agent_commands(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
):

    dispatcher = AgentDispatcher(db)

    commands = dispatcher.get_pending_commands(agent_id)

    return commands