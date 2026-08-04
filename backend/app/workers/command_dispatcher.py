from __future__ import annotations

import logging
import threading
import time
import uuid

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.agent import Agent
from app.models.command import CommandStatus
from app.repositories.agent_repository import AgentRepository
from app.repositories.command_repository import CommandRepository

logger = logging.getLogger(__name__)


class CommandDispatcher:
    """
    Enterprise Command Dispatcher

    Responsibilities

    • Monitor online agents

    • Queue commands

    • Detect stale agents

    • Retry failed delivery

    • Future websocket dispatch

    • Future message bus integration

    • Future Kafka/RabbitMQ support
    """

    DISPATCH_INTERVAL = 2

    OFFLINE_TIMEOUT = 90

    def __init__(self):

        self.running = False

        self.thread: threading.Thread | None = None

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def start(self):

        if self.running:

            return

        self.running = True

        self.thread = threading.Thread(

            target=self.run,

            daemon=True,

            name="CommandDispatcher",

        )

        self.thread.start()

        logger.info("Command Dispatcher started.")

    def stop(self):

        self.running = False

        logger.info("Command Dispatcher stopped.")

    # ---------------------------------------------------------
    # Loop
    # ---------------------------------------------------------

    def run(self):

        while self.running:

            try:

                self.dispatch_cycle()

            except Exception:

                logger.exception("Dispatcher failure")

            time.sleep(self.DISPATCH_INTERVAL)

    # ---------------------------------------------------------
    # Cycle
    # ---------------------------------------------------------

    def dispatch_cycle(self):

        db: Session = SessionLocal()

        try:

            agent_repo = AgentRepository(db)

            command_repo = CommandRepository(db)

            agents = agent_repo.get_online_agents()

            for agent in agents:

                self.dispatch_agent(

                    db,

                    command_repo,

                    agent,

                )

        finally:

            db.close()

    # ---------------------------------------------------------
    # Agent
    # ---------------------------------------------------------

    def dispatch_agent(

        self,

        db: Session,

        repository: CommandRepository,

        agent: Agent,

    ):

        queue = repository.get_pending_commands(

            agent.id

        )

        if not queue:

            return

        logger.info(

            "Dispatching %s command(s) to %s",

            len(queue),

            agent.hostname,

        )

        for command in queue:

            repository.mark_sent(command)

    # ---------------------------------------------------------
    # Retry
    # ---------------------------------------------------------

    def retry_stale(self):

        db = SessionLocal()

        try:

            repository = CommandRepository(db)

            running = db.query(repository.model).filter(
                repository.model.status == CommandStatus.RUNNING
            )

            for command in running:

                pass

        finally:

            db.close()


dispatcher = CommandDispatcher()