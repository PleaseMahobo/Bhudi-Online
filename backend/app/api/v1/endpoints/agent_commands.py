from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.agent_dispatcher import AgentDispatcher

router = APIRouter(prefix="/agent", tags=["Agent Commands"])


@router.get("/{agent_id}/commands")
def get_commands(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    dispatcher = AgentDispatcher(db)

    commands = dispatcher.get_pending_commands(agent_id)

    return [
        {
            "id": str(command.id),
            "command_id": str(command.id),
            "command_type": command.command_type,
            "payload": command.payload,
            "priority": command.priority,
            "timeout_seconds": command.timeout_seconds,
            "requires_reboot": command.requires_reboot,
            "status": command.status,
            "queued_at": command.queued_at,
        }
        for command in commands
    ]


@router.post("/{agent_id}/commands/{command_id}/sent")
def mark_sent(
    agent_id: uuid.UUID,
    command_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    dispatcher = AgentDispatcher(db)

    dispatcher.mark_sent(command_id)

    return {"status": "ok"}


@router.post("/{agent_id}/commands/{command_id}/completed")
def mark_completed(
    agent_id: uuid.UUID,
    command_id: uuid.UUID,
    result: dict,
    db: Session = Depends(get_db),
):
    dispatcher = AgentDispatcher(db)

    dispatcher.mark_completed(command_id, result)

    return {"status": "ok"}


@router.post("/{agent_id}/commands/{command_id}/failed")
def mark_failed(
    agent_id: uuid.UUID,
    command_id: uuid.UUID,
    error: dict,
    db: Session = Depends(get_db),
):
    dispatcher = AgentDispatcher(db)

    dispatcher.mark_failed(
        command_id,
        error.get("message", "Unknown error"),
    )

    return {"status": "ok"}