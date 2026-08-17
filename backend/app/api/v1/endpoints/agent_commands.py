from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.agent import Agent
from app.services.agent_dispatcher import AgentDispatcher

router = APIRouter(prefix="/agent", tags=["Agent Commands"])


def _require_agent(agent_id: uuid.UUID, agent_token: str | None, db: Session) -> Agent:
    agent = db.get(Agent, agent_id)
    stored = agent.enrollment_token if agent else None
    if not agent or not agent.enabled or not agent_token or not stored or not secrets.compare_digest(agent_token, stored):
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    return agent


def _require_command_agent(agent_id: uuid.UUID, command_id: uuid.UUID, db: Session) -> None:
    from app.models.agent_command import AgentCommand

    command = db.get(AgentCommand, command_id)
    if command is None or command.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Command not found")


@router.get("/{agent_id}/commands")
def get_commands(
    agent_id: uuid.UUID,
    agent_token: str | None = None,
    db: Session = Depends(get_db),
):
    _require_agent(agent_id, agent_token, db)
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
    agent_token: str | None = None,
    db: Session = Depends(get_db),
):
    _require_agent(agent_id, agent_token, db)
    _require_command_agent(agent_id, command_id, db)
    AgentDispatcher(db).mark_sent(command_id)
    return {"status": "ok"}


@router.post("/{agent_id}/commands/{command_id}/completed")
def mark_completed(
    agent_id: uuid.UUID,
    command_id: uuid.UUID,
    result: dict,
    agent_token: str | None = None,
    db: Session = Depends(get_db),
):
    _require_agent(agent_id, agent_token, db)
    _require_command_agent(agent_id, command_id, db)
    AgentDispatcher(db).mark_completed(command_id, result)
    return {"status": "ok"}


@router.post("/{agent_id}/commands/{command_id}/failed")
def mark_failed(
    agent_id: uuid.UUID,
    command_id: uuid.UUID,
    error: dict,
    agent_token: str | None = None,
    db: Session = Depends(get_db),
):
    _require_agent(agent_id, agent_token, db)
    _require_command_agent(agent_id, command_id, db)
    AgentDispatcher(db).mark_failed(command_id, error.get("message", "Unknown error"))
    return {"status": "ok"}
