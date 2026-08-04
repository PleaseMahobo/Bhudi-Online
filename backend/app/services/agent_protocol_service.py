from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.repositories.agent_repository import AgentRepository
from app.services.command_service import CommandService


class AgentProtocolService:

    """
    Enterprise communication protocol.

    Every agent talks to the server only
    through this service.
    """

    def __init__(self, db: Session):

        self.db = db

        self.agents = AgentRepository(db)

        self.commands = CommandService(db)

    # --------------------------------------------------
    # Registration
    # --------------------------------------------------

    def register(
        self,
        request,
    ):

        raise NotImplementedError

    # --------------------------------------------------
    # Heartbeat
    # --------------------------------------------------

    def heartbeat(
        self,
        heartbeat,
    ):

        raise NotImplementedError

    # --------------------------------------------------
    # Poll
    # --------------------------------------------------

    def poll(
        self,
        agent_id: uuid.UUID,
    ):

        return self.commands.poll(agent_id)

    # --------------------------------------------------
    # Result
    # --------------------------------------------------

    def submit_result(
        self,
        command_id,
        stdout,
        stderr,
        exit_code,
    ):

        return self.commands.submit_result(

            command_id=command_id,

            stdout=stdout,

            stderr=stderr,

            exit_code=exit_code,

        )