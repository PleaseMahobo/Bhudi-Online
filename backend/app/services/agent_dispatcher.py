from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.agent_command import AgentCommand
from app.repositories.agent_repository import AgentRepository
from app.repositories.agent_command_repository import AgentCommandRepository


class AgentDispatcher:
    """
    Enterprise command dispatcher.

    Responsibilities
    ----------------
    • Validate target agent
    • Queue commands
    • Maintain audit trail
    • Return command identifiers
    """

    def __init__(self, db: Session):
        self.db = db

        self.agent_repo = AgentRepository(db)
        self.command_repo = AgentCommandRepository(db)

    def queue_command(
        self,
        *,
        agent_id: uuid.UUID,
        command_type: str,
        payload: dict[str, Any] | None = None,
        requested_by: uuid.UUID | None = None,
        priority: int = 5,
    ) -> AgentCommand:

        agent = self.agent_repo.get(agent_id)

        if agent is None:
            raise ValueError("Agent not found.")

        if not agent.enabled:
            raise ValueError("Agent disabled.")

        command = AgentCommand(
            agent_id=agent.id,
            command_type=command_type,
            payload=payload or {},
            priority=priority,
            requested_by=requested_by,
        )

        return self.command_repo.create(command)

    def get_pending_commands(
        self,
        agent_id: uuid.UUID,
    ) -> list[AgentCommand]:

        return self.command_repo.pending_for_agent(agent_id)

    def mark_sent(
        self,
        command_id: uuid.UUID,
    ) -> AgentCommand:

        command = self.command_repo.get(command_id)

        if command is None:
            raise ValueError("Command not found.")

        command.mark_sent()

        self.db.commit()
        self.db.refresh(command)

        return command

    def mark_completed(
        self,
        command_id: uuid.UUID,
        result: dict | None = None,
    ) -> AgentCommand:

        command = self.command_repo.get(command_id)

        if command is None:
            raise ValueError("Command not found.")

        command.mark_completed(result)

        self.db.commit()
        self.db.refresh(command)

        return command

    def mark_failed(
        self,
        command_id: uuid.UUID,
        error: str,
    ) -> AgentCommand:

        command = self.command_repo.get(command_id)

        if command is None:
            raise ValueError("Command not found.")

        command.mark_failed(error)

        self.db.commit()
        self.db.refresh(command)

        return command