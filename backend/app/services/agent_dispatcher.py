from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
        timeout_seconds: int | None = None,
        requires_reboot: bool = False,
    ) -> AgentCommand:

        agent = self.agent_repo.get(agent_id)

        if agent is None:
            raise ValueError("Agent not found.")

        if not agent.enabled:
            raise ValueError("Agent disabled.")

        command = AgentCommand(
            id=uuid.uuid4(),
            agent_id=agent.id,
            command_type=command_type,
            payload=payload or {},
            priority=priority,
            issued_by=requested_by,
            timeout_seconds=timeout_seconds or agent.command_timeout,
            requires_reboot=requires_reboot,
        )
        command = self.command_repo.create(command)
        self.db.commit()
        self.db.refresh(command)
        return command

    def get_pending_commands(
        self,
        agent_id: uuid.UUID,
    ) -> list[AgentCommand]:
        return self.command_repo.get_pending_commands(agent_id)

    def mark_sent(
        self,
        command_id: uuid.UUID,
    ) -> AgentCommand:

        command = self.command_repo.get(command_id)

        if command is None:
            raise ValueError("Command not found.")

        self.command_repo.mark_dispatched(command_id)

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

        if command.started_at is None:
            self.command_repo.mark_running(command_id)

        exit_code = int((result or {}).get("exit_code", 0))
        stdout = (result or {}).get("stdout", "")
        stderr = (result or {}).get("stderr", "")
        command_result = result or {}

        self.command_repo.complete(
            command_id,
            exit_code,
            stdout,
            stderr,
            command_result,
        )

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

        self.command_repo.fail(
            command_id,
            error,
            {"error": error, "failed_at": datetime.now(timezone.utc).isoformat()},
        )

        self.db.commit()
        self.db.refresh(command)

        return command