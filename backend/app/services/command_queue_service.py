from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.command import (
    Command,
    CommandStatus,
)

from app.repositories.command_repository import (
    CommandRepository,
)


class CommandQueueService:
    """
    Enterprise Command Queue

    Responsible for

    • queue scheduling

    • offline persistence

    • retries

    • acknowledgement

    • timeout detection

    • stale cleanup
    """

    DEFAULT_RETRY_LIMIT = 3

    ACK_TIMEOUT = 60

    EXECUTION_TIMEOUT = 300

    def __init__(
        self,
        db: Session,
    ):

        self.db = db

        self.repository = CommandRepository(db)

    # ----------------------------------------------------------
    # Queue
    # ----------------------------------------------------------

    def queue(
        self,
        command: Command,
    ) -> Command:

        command.status = CommandStatus.QUEUED

        return self.repository.create(command)

    # ----------------------------------------------------------
    # Agent Poll
    # ----------------------------------------------------------

    def dequeue(
        self,
        agent_id: uuid.UUID,
    ) -> list[Command]:

        commands = self.repository.get_pending_commands(
            agent_id
        )

        for command in commands:

            self.repository.mark_sent(command)

        return commands

    # ----------------------------------------------------------
    # Agent ACK
    # ----------------------------------------------------------

    def acknowledge(
        self,
        command_id: uuid.UUID,
    ):

        command = self.repository.get(command_id)

        if command is None:

            return

        self.repository.mark_running(command)

    # ----------------------------------------------------------
    # Timeout Detection
    # ----------------------------------------------------------

    def detect_timeouts(
        self,
    ) -> list[Command]:

        timed_out = []

        now = datetime.utcnow()

        for command in self.db.query(Command).filter(

            Command.status == CommandStatus.RUNNING

        ):

            if command.started_at is None:

                continue

            timeout = timedelta(
                seconds=command.timeout_seconds
            )

            if now > command.started_at + timeout:

                self.repository.timeout(command)

                timed_out.append(command)

        return timed_out

    # ----------------------------------------------------------
    # Retry
    # ----------------------------------------------------------

    def retry_failed(
        self,
        command_id: uuid.UUID,
    ):

        command = self.repository.get(command_id)

        if command is None:

            return None

        command.status = CommandStatus.QUEUED

        command.started_at = None

        command.completed_at = None

        command.stdout = None

        command.stderr = None

        command.exit_code = None

        self.db.commit()

        self.db.refresh(command)

        return command

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------

    def cleanup_completed(
        self,
        older_than_days: int = 90,
    ):

        cutoff = datetime.utcnow() - timedelta(
            days=older_than_days
        )

        completed = (

            self.db.query(Command)

            .filter(

                Command.completed_at < cutoff,

            )

            .all()

        )

        count = len(completed)

        for command in completed:

            self.db.delete(command)

        self.db.commit()

        return count