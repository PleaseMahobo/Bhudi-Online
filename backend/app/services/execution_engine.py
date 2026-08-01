from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.command import Command, CommandStatus
from app.repositories.command_repository import CommandRepository

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Enterprise Command Execution Engine.

    Responsibilities
    ----------------
    • Queue commands
    • Validate execution
    • Start execution
    • Cancel execution
    • Retry failed execution
    • Complete execution
    • Maintain audit state
    """

    def __init__(self, db: Session):

        self.db = db
        self.commands = CommandRepository(db)

    # -----------------------------------------------------
    # Queue
    # -----------------------------------------------------

    def queue(self, command: Command) -> Command:

        command.status = CommandStatus.PENDING
        command.created_at = datetime.now(timezone.utc)

        self.db.add(command)
        self.db.commit()
        self.db.refresh(command)

        logger.info(
            "Queued command %s for agent %s",
            command.id,
            command.agent_id,
        )

        return command

    # -----------------------------------------------------
    # Start
    # -----------------------------------------------------

    def mark_running(self, command_id: uuid.UUID) -> Command:

        command = self.commands.get(command_id)

        if command is None:
            raise ValueError("Command not found")

        command.status = CommandStatus.RUNNING
        command.started_at = datetime.now(timezone.utc)

        self.db.commit()

        logger.info(
            "Started command %s",
            command.id,
        )

        return command

    # -----------------------------------------------------
    # Complete
    # -----------------------------------------------------

    def complete(

        self,

        command_id: uuid.UUID,

        stdout: str,

        stderr: str,

        exit_code: int,

    ) -> Command:

        command = self.commands.get(command_id)

        if command is None:
            raise ValueError("Command not found")

        command.stdout = stdout
        command.stderr = stderr
        command.exit_code = exit_code

        command.completed_at = datetime.now(timezone.utc)

        if exit_code == 0:
            command.status = CommandStatus.SUCCESS
        else:
            command.status = CommandStatus.FAILED

        self.db.commit()

        logger.info(
            "Completed command %s",
            command.id,
        )

        return command

    # -----------------------------------------------------
    # Cancel
    # -----------------------------------------------------

    def cancel(self, command_id: uuid.UUID):

        command = self.commands.get(command_id)

        if command is None:
            raise ValueError("Command not found")

        command.status = CommandStatus.CANCELLED

        command.completed_at = datetime.now(timezone.utc)

        self.db.commit()

        logger.info(
            "Cancelled command %s",
            command.id,
        )

    # -----------------------------------------------------
    # Retry
    # -----------------------------------------------------

    def retry(self, command_id: uuid.UUID):

        command = self.commands.get(command_id)

        if command is None:
            raise ValueError("Command not found")

        command.status = CommandStatus.PENDING

        command.started_at = None
        command.completed_at = None
        command.stdout = None
        command.stderr = None
        command.exit_code = None

        self.db.commit()

        logger.info(
            "Retrying command %s",
            command.id,
        )