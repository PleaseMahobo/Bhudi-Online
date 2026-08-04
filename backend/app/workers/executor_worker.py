from __future__ import annotations

import logging
import threading
import time

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.agent_command import CommandStatus
from app.models.agent_command import AgentCommand
from app.models.agent_command import AgentCommand


from app.repositories.agent_command_repository import AgentCommandRepository

logger = logging.getLogger(__name__)


class ExecutorWorker:
    """
    Enterprise Command Executor Worker.

    Responsibilities
    ----------------

    • Scan queued commands
    • Dispatch pending work
    • Retry failed work
    • Expire stale work
    • Detect timeouts
    • Maintain execution lifecycle

    Runs continuously as a daemon thread.
    """

    INTERVAL = 2

    def __init__(self):

        self.running = False

        self.thread: threading.Thread | None = None

    ###########################################################
    # Lifecycle
    ###########################################################

    def start(self):

        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(

            target=self.run,

            daemon=True,

            name="ExecutorWorker",

        )

        self.thread.start()

        logger.info("Executor Worker started.")

    def stop(self):

        self.running = False

        logger.info("Executor Worker stopped.")

    ###########################################################
    # Main Loop
    ###########################################################

    def run(self):

        while self.running:

            try:

                self.execute_cycle()

            except Exception:

                logger.exception("Executor cycle failed.")

            time.sleep(self.INTERVAL)

    ###########################################################
    # Cycle
    ###########################################################

    def execute_cycle(self):

        db: Session = SessionLocal()

        try:

            repository = AgentCommandRepository(db)

            #
            # Expire Commands
            #

            expired = repository.expired_commands()

            for command in expired:

                command.status = CommandStatus.EXPIRED.value

            #
            # Retry Logic
            #

            retry_list = self._retry_candidates(db)

            for command in retry_list:

                repository.retry(command.id)

            db.commit()

        finally:

            db.close()

    ###########################################################
    # Retry Selection
    ###########################################################

    def _retry_candidates(self, db: Session):

        return (
            db.query(AgentCommand)
            .filter(
                AgentCommand.status == CommandStatus.FAILED.value,
                AgentCommand.retry_count < AgentCommand.max_retries,
            )
            .all()
        )

executor_worker = ExecutorWorker()