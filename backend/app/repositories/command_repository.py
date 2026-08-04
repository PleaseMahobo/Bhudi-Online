from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import (
    Command,
    CommandStatus,
)


class CommandRepository:
    """
    Enterprise Command Repository

    Centralized persistence layer for
    command queue management.
    """

    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------

    def create(
        self,
        command: Command,
    ) -> Command:

        self.db.add(command)
        self.db.commit()
        self.db.refresh(command)

        return command

    def get(
        self,
        command_id: uuid.UUID,
    ) -> Command | None:

        return self.db.get(
            Command,
            command_id,
        )

    def delete(
        self,
        command: Command,
    ) -> None:

        self.db.delete(command)
        self.db.commit()

    # ----------------------------------------------------------
    # Agent Queue
    # ----------------------------------------------------------

    def get_pending_commands(
        self,
        agent_id: uuid.UUID,
    ) -> list[Command]:

        stmt = (
            select(Command)
            .where(
                Command.agent_id == agent_id,
                Command.status == CommandStatus.QUEUED,
            )
            .order_by(Command.created_at.asc())
        )

        return list(
            self.db.scalars(stmt)
        )

    def get_running_commands(
        self,
        agent_id: uuid.UUID,
    ) -> list[Command]:

        stmt = (
            select(Command)
            .where(
                Command.agent_id == agent_id,
                Command.status == CommandStatus.RUNNING,
            )
        )

        return list(
            self.db.scalars(stmt)
        )

    def get_command_history(
        self,
        agent_id: uuid.UUID,
        limit: int = 100,
    ) -> list[Command]:

        stmt = (
            select(Command)
            .where(
                Command.agent_id == agent_id,
            )
            .order_by(
                Command.created_at.desc()
            )
            .limit(limit)
        )

        return list(
            self.db.scalars(stmt)
        )

    # ----------------------------------------------------------
    # Status Updates
    # ----------------------------------------------------------

    def mark_sent(
        self,
        command: Command,
    ) -> Command:

        command.status = CommandStatus.SENT

        self.db.commit()
        self.db.refresh(command)

        return command

    def mark_running(
        self,
        command: Command,
    ) -> Command:

        command.status = CommandStatus.RUNNING
        command.started_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(command)

        return command

    def complete(
        self,
        command: Command,
        *,
        stdout: str | None,
        stderr: str | None,
        exit_code: int | None,
        success: bool,
    ) -> Command:

        command.stdout = stdout
        command.stderr = stderr
        command.exit_code = exit_code

        command.completed_at = datetime.now(timezone.utc)

        command.status = (
            CommandStatus.SUCCESS
            if success
            else CommandStatus.FAILED
        )

        self.db.commit()
        self.db.refresh(command)

        return command

    def cancel(
        self,
        command: Command,
    ) -> Command:

        command.status = CommandStatus.CANCELLED

        command.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(command)

        return command

    def timeout(
        self,
        command: Command,
    ) -> Command:

        command.status = CommandStatus.TIMED_OUT

        command.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(command)

        return command