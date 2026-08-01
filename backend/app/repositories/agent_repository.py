from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.repositories.base_repository import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    """
    Enterprise repository for Bhudi Agent management.

    Responsibilities
    ----------------
    • Device enrollment
    • Agent lifecycle
    • Heartbeats
    • Version tracking
    • Update management
    • Revocation
    """

    def __init__(self, session: Session):
        super().__init__(session, Agent)

    # ==========================================================
    # Identity
    # ==========================================================

    def get(
        self,
        agent_id: uuid.UUID,
    ) -> Agent | None:

        return self.session.get(
            Agent,
            agent_id,
        )

    def get_by_uuid(
        self,
        agent_uuid: uuid.UUID,
    ) -> Agent | None:

        stmt = (
            select(Agent)
            .where(
                Agent.agent_uuid == agent_uuid
            )
        )

        return self.session.scalar(stmt)

    def get_by_device(
        self,
        device_id: uuid.UUID,
    ) -> Agent | None:

        stmt = (
            select(Agent)
            .where(
                Agent.device_id == device_id
            )
        )

        return self.session.scalar(stmt)

    def get_by_hostname(
        self,
        hostname: str,
    ) -> Agent | None:

        stmt = (
            select(Agent)
            .where(
                Agent.hostname == hostname
            )
        )

        return self.session.scalar(stmt)

    # ==========================================================
    # Registration
    # ==========================================================

    def pending_agents(
        self,
    ) -> list[Agent]:

        stmt = (
            select(Agent)
            .where(
                Agent.registration_state == "pending"
            )
            .order_by(
                Agent.created_at.asc()
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    def approved_agents(
        self,
    ) -> list[Agent]:

        stmt = (
            select(Agent)
            .where(
                Agent.registration_state == "approved"
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    # ==========================================================
    # Status
    # ==========================================================

    def online_agents(
        self,
    ) -> list[Agent]:

        stmt = (
            select(Agent)
            .where(
                Agent.status == "online"
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    def offline_agents(
        self,
    ) -> list[Agent]:

        stmt = (
            select(Agent)
            .where(
                Agent.status == "offline"
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    def quarantined_agents(
        self,
    ) -> list[Agent]:

        stmt = (
            select(Agent)
            .where(
                Agent.quarantined.is_(True)
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    # ==========================================================
    # Heartbeat
    # ==========================================================

    def heartbeat(
        self,
        agent: Agent,
        *,
        ip_address: str | None,
        username: str | None,
    ) -> Agent:

        now = datetime.utcnow()

        agent.last_heartbeat = now
        agent.last_checkin = now
        agent.last_seen = now
        agent.last_ip_address = ip_address
        agent.last_logged_on_user = username
        agent.status = "online"

        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)

        return agent

    # ==========================================================
    # Updates
    # ==========================================================

    def agents_needing_update(
        self,
    ) -> list[Agent]:

        stmt = (
            select(Agent)
            .where(
                Agent.update_available.is_(True)
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def revoke(
        self,
        agent: Agent,
        reason: str,
    ) -> Agent:

        agent.revoked = True
        agent.status = "revoked"
        agent.revocation_reason = reason
        agent.revoked_at = datetime.utcnow()

        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)

        return agent

    def quarantine(
        self,
        agent: Agent,
    ) -> Agent:

        agent.quarantined = True
        agent.status = "quarantined"

        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)

        return agent

    def restore(
        self,
        agent: Agent,
    ) -> Agent:

        agent.quarantined = False
        agent.revoked = False
        agent.status = "online"

        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)

        return agent