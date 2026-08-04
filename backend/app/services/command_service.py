from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.agent_command import (
    AgentCommand,
    CommandPriority,
    CommandStatus,
)
from app.repositories.agent_command_repository import AgentCommandRepository
from app.repositories.agent_repository import AgentRepository


class CommandService:
    """
    Enterprise Command Orchestration Service.

    Responsibilities

    • Queue commands
    • Validate agent state
    • Assign priorities
    • Retry failed jobs
    • Handle expirations
    • Handle acknowledgements
    • Complete execution
    """

    DEFAULT_TIMEOUT = 300

    def __init__(self, db: Session):

        self.db = db
        self.commands = AgentCommandRepository(db)
        self.agents = AgentRepository(db)

    ####################################################################
    # Validation
    ####################################################################

    def _validate_agent(
        self,
        agent_id: uuid.UUID,
    ) -> Agent:

        agent = self.agents.get(agent_id)

        if agent is None:
            raise ValueError("Agent does not exist.")

        if not agent.enabled:
            raise ValueError("Agent disabled.")

        if not agent.approved:
            raise ValueError("Agent not approved.")

        return agent

    ####################################################################
    # Queue
    ####################################################################

    def queue_command(
        self,
        *,
        agent_id: uuid.UUID,
        command: str,
        arguments: dict | None = None,
        priority: CommandPriority = CommandPriority.NORMAL,
        timeout: int | None = None,
        created_by: uuid.UUID | None = None,
        expires_minutes: int = 60,
    ) -> AgentCommand:

        self._validate_agent(agent_id)

        timeout = timeout or self.DEFAULT_TIMEOUT

        cmd = AgentCommand(
            agent_id=agent_id,
            command=command,
            arguments=arguments,
            priority=priority.value,
            timeout=timeout,
            created_by=created_by,
            status=CommandStatus.PENDING.value,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=expires_minutes),
        )

        self.commands.create(cmd)

        self.db.commit()

        self.db.refresh(cmd)

        return cmd

    ####################################################################
    # Poll
    ####################################################################

    def poll(
        self,
        agent_id: uuid.UUID,
    ) -> list[AgentCommand]:

        self._validate_agent(agent_id)

        commands = self.commands.get_pending_commands(agent_id)

        for command in commands:

            self.commands.mark_dispatched(command.id)

        self.db.commit()

        return commands

    ####################################################################
    # Running
    ####################################################################

    def acknowledge(
        self,
        command_id: uuid.UUID,
    ):

        self.commands.mark_running(command_id)

        self.db.commit()

    ####################################################################
    # Completion
    ####################################################################

    def complete(
        self,
        *,
        command_id: uuid.UUID,
        exit_code: int,
        stdout: str,
        stderr: str,
        result: dict | None = None,
    ):

        self.commands.complete(
            command_id,
            exit_code,
            stdout,
            stderr,
            result,
        )

        self.db.commit()

    ####################################################################
    # Retry
    ####################################################################

    def retry(
        self,
        command_id: uuid.UUID,
    ):

        self.commands.retry(command_id)

        self.db.commit()

    ####################################################################
    # Maintenance
    ####################################################################

    def expire_commands(self):

        expired = self.commands.expired_commands()

        for cmd in expired:

            cmd.status = CommandStatus.EXPIRED.value

        self.db.commit()

        return len(expired)

    ####################################################################
    # Bulk Queue
    ####################################################################

    def queue_bulk(
        self,
        *,
        agent_ids: list[uuid.UUID],
        command: str,
        arguments: dict | None = None,
        priority: CommandPriority = CommandPriority.NORMAL,
    ) -> list[AgentCommand]:

        created = []

        for agent in agent_ids:

            try:

                created.append(
                    self.queue_command(
                        agent_id=agent,
                        command=command,
                        arguments=arguments,
                        priority=priority,
                    )
                )

            except Exception:

                continue

        return created