from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository
from app.repositories.device_repository import DeviceRepository
from app.core.security import (
    hash_password,
    verify_password,
)


class AgentService:
    """
    Enterprise Agent Service.

    Responsibilities

    • Enrollment
    • Authentication
    • Heartbeats
    • Update management
    • Lifecycle
    • Quarantine
    • Revocation
    """

    def __init__(
        self,
        db: Session,
    ):

        self.db = db
        self.agents = AgentRepository(db)
        self.devices = DeviceRepository(db)

    # ==========================================================
    # Enrollment
    # ==========================================================

    def enroll(
        self,
        *,
        device_id: uuid.UUID,
        hostname: str,
        version: str,
        enrollment_secret: str,
    ) -> Agent:

        existing = self.agents.get_by_device(
            device_id
        )

        if existing:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Device already enrolled.",
            )

        agent = Agent()

        agent.agent_uuid = uuid.uuid4()
        agent.device_id = device_id
        agent.hostname = hostname
        agent.agent_version = version

        agent.registration_state = "pending"

        agent.enrollment_secret_hash = (
            hash_password(
                enrollment_secret
            )
        )

        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)

        return agent

    # ==========================================================
    # Approval
    # ==========================================================

    def approve(
        self,
        agent_id: uuid.UUID,
        approver: uuid.UUID,
    ) -> Agent:

        agent = self.agents.get(agent_id)

        if not agent:

            raise HTTPException(
                status_code=404,
                detail="Agent not found.",
            )

        agent.registration_state = "approved"

        agent.approved_at = datetime.utcnow()

        agent.approved_by = approver

        self.db.commit()
        self.db.refresh(agent)

        return agent

    # ==========================================================
    # Authentication
    # ==========================================================

    def authenticate(
        self,
        *,
        agent_uuid: uuid.UUID,
        enrollment_secret: str,
    ) -> Agent:

        agent = self.agents.get_by_uuid(
            agent_uuid
        )

        if not agent:

            raise HTTPException(
                status_code=401,
                detail="Unknown agent.",
            )

        if agent.revoked:

            raise HTTPException(
                status_code=403,
                detail="Agent revoked.",
            )

        if not verify_password(
            enrollment_secret,
            agent.enrollment_secret_hash,
        ):

            raise HTTPException(
                status_code=401,
                detail="Authentication failed.",
            )

        return agent

    # ==========================================================
    # Heartbeat
    # ==========================================================

    def heartbeat(
        self,
        *,
        agent_uuid: uuid.UUID,
        ip_address: str | None,
        username: str | None,
    ) -> Agent:

        agent = self.agents.get_by_uuid(
            agent_uuid
        )

        if not agent:

            raise HTTPException(
                status_code=404,
                detail="Unknown agent.",
            )

        return self.agents.heartbeat(
            agent,
            ip_address=ip_address,
            username=username,
        )

    # ==========================================================
    # Updates
    # ==========================================================

    def mark_update_available(
        self,
        agent_id: uuid.UUID,
        target_version: str,
    ) -> Agent:

        agent = self.agents.get(agent_id)

        if not agent:

            raise HTTPException(
                status_code=404,
                detail="Agent not found.",
            )

        agent.update_available = True
        agent.target_version = target_version

        self.db.commit()
        self.db.refresh(agent)

        return agent

    def complete_update(
        self,
        *,
        agent_uuid: uuid.UUID,
        installed_version: str,
    ) -> Agent:

        agent = self.agents.get_by_uuid(
            agent_uuid
        )

        if not agent:

            raise HTTPException(
                status_code=404,
                detail="Unknown agent.",
            )

        agent.agent_version = installed_version

        agent.last_update = datetime.utcnow()

        agent.update_available = False

        agent.target_version = None

        self.db.commit()
        self.db.refresh(agent)

        return agent

    # ==========================================================
    # Security
    # ==========================================================

    def quarantine(
        self,
        agent_id: uuid.UUID,
    ) -> Agent:

        agent = self.agents.get(agent_id)

        if not agent:

            raise HTTPException(
                status_code=404,
                detail="Agent not found.",
            )

        return self.agents.quarantine(
            agent
        )

    def revoke(
        self,
        *,
        agent_id: uuid.UUID,
        reason: str,
    ) -> Agent:

        agent = self.agents.get(agent_id)

        if not agent:

            raise HTTPException(
                status_code=404,
                detail="Agent not found.",
            )

        return self.agents.revoke(
            agent,
            reason,
        )

    def restore(
        self,
        agent_id: uuid.UUID,
    ) -> Agent:

        agent = self.agents.get(agent_id)

        if not agent:

            raise HTTPException(
                status_code=404,
                detail="Agent not found.",
            )

        return self.agents.restore(
            agent
        )