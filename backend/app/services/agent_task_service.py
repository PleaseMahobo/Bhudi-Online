from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.agent_command import AgentCommand
from app.models.command_status import CommandStatus
from app.repositories.agent_command_repository import AgentCommandRepository


class AgentTaskService:
    """
    Production task dispatcher.

    Responsible for:

    • Returning queued commands
    • Locking commands
    • Marking delivery
    • Completing commands
    • Handling failures
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = AgentCommandRepository(db)

    def get_pending_commands(
        self,
        agent_id: uuid.UUID,
        limit: int = 50,
    ) -> list[AgentCommand]:

        return (
            self.db.query(AgentCommand)
            .filter(
                AgentCommand.agent_id == agent_id,
                AgentCommand.status == CommandStatus.QUEUED,
            )
            .order_by(
                AgentCommand.priority.desc(),
                AgentCommand.created_at.asc(),
            )
            .limit(limit)
            .all()
        )

    def mark_dispatched(
        self,
        command: AgentCommand,
    ) -> AgentCommand:

        command.status = CommandStatus.DISPATCHED
        command.dispatched_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(command)

        return command

    def mark_running(
        self,
        command: AgentCommand,
    ) -> AgentCommand:

        command.status = CommandStatus.RUNNING

        self.db.commit()
        self.db.refresh(command)

        return command

    def complete(
        self,
        command: AgentCommand,
        output: str | None = None,
    ) -> AgentCommand:

        command.status = CommandStatus.COMPLETED
        command.completed_at = datetime.now(timezone.utc)
        command.output = output

        self.db.commit()
        self.db.refresh(command)

        return command

    def fail(
        self,
        command: AgentCommand,
        error: str,
    ) -> AgentCommand:

        command.status = CommandStatus.FAILED
        command.completed_at = datetime.now(timezone.utc)
        command.error = error

        self.db.commit()
        self.db.refresh(command)

        return command

    def cancel(
        self,
        command: AgentCommand,
    ) -> AgentCommand:

        command.status = CommandStatus.CANCELLED

        self.db.commit()
        self.db.refresh(command)

        return command