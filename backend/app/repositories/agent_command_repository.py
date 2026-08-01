from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from app.models.agent_command import (
    AgentCommand,
    CommandStatus,
)


class AgentCommandRepository:
    """
    Production repository for queued agent commands.

    Optimized for:

    • High polling rates
    • Thousands of agents
    • Minimal locking
    • Transaction safety
    """

    def __init__(self, db: Session):

        self.db = db

        self.model = AgentCommand

    ############################################################
    # CRUD
    ############################################################

    def create(self, command: AgentCommand) -> AgentCommand:
        self.db.add(command)
        self.db.flush()
        self.db.refresh(command)
        return command

    def get(self, command_id: uuid.UUID) -> AgentCommand | None:
        return self.db.get(AgentCommand, command_id)

    ############################################################
    # Agent Polling
    ############################################################

    def get_pending_commands(
        self,
        agent_id: uuid.UUID,
        limit: int = 50,
    ) -> list[AgentCommand]:

        stmt = (
            select(AgentCommand)
            .where(
                and_(
                    AgentCommand.agent_id == agent_id,
                    AgentCommand.status == CommandStatus.PENDING.value,
                )
            )
            .order_by(
                AgentCommand.priority.desc(),
                AgentCommand.queued_at.asc(),
            )
            .limit(limit)
        )

        return list(self.db.scalars(stmt).all())

    ############################################################
    # Dispatch
    ############################################################

    def mark_dispatched(
        self,
        command_id: uuid.UUID,
    ) -> None:

        self.db.execute(
            update(AgentCommand)
            .where(AgentCommand.id == command_id)
            .values(
                status=CommandStatus.DISPATCHED.value,
                acknowledged=True,
            )
        )

    ############################################################
    # Running
    ############################################################

    def mark_running(
        self,
        command_id: uuid.UUID,
    ) -> None:

        self.db.execute(
            update(AgentCommand)
            .where(AgentCommand.id == command_id)
            .values(
                status=CommandStatus.RUNNING.value,
                started_at=datetime.utcnow(),
            )
        )

    ############################################################
    # Completion
    ############################################################

    def complete(
        self,
        command_id: uuid.UUID,
        exit_code: int,
        stdout: str,
        stderr: str,
        result: dict | None = None,
    ) -> None:

        status = (
            CommandStatus.COMPLETED.value
            if exit_code == 0
            else CommandStatus.FAILED.value
        )

        self.db.execute(
            update(AgentCommand)
            .where(AgentCommand.id == command_id)
            .values(
                status=status,
                completed_at=datetime.utcnow(),
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                result=result,
            )
        )

    ############################################################
    # Retry
    ############################################################

    def retry(
        self,
        command_id: uuid.UUID,
    ) -> None:

        command = self.get(command_id)

        if command is None:
            return

        self.db.execute(
            update(AgentCommand)
            .where(AgentCommand.id == command_id)
            .values(
                retry_count=command.retry_count + 1,
                status=CommandStatus.PENDING.value,
            )
        )

    ############################################################
    # Cleanup
    ############################################################

    def expired_commands(self) -> list[AgentCommand]:

        stmt = (
            select(AgentCommand)
            .where(
                and_(
                    AgentCommand.expires_at.is_not(None),
                    AgentCommand.expires_at < datetime.utcnow(),
                    AgentCommand.status.in_(
                        [
                            CommandStatus.PENDING.value,
                            CommandStatus.DISPATCHED.value,
                            CommandStatus.RUNNING.value,
                        ]
                    ),
                )
            )
        )

        return list(self.db.scalars(stmt).all())

    ############################################################
    # Statistics
    ############################################################

    def count_pending(
        self,
        agent_id: uuid.UUID,
    ) -> int:

        stmt = (
            select(AgentCommand)
            .where(
                and_(
                    AgentCommand.agent_id == agent_id,
                    AgentCommand.status == CommandStatus.PENDING.value,
                )
            )
        )

        return len(list(self.db.scalars(stmt)))