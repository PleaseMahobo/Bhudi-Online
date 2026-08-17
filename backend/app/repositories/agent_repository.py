from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.repositories.base_repository import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    """
    Enterprise repository for Bhudi Agent management.

    Tenant isolation is enforced here for portal-facing lookups. Callers that
    operate on an agent on behalf of the agent itself may use the unscoped
    identity methods only where the agent credential has already authenticated.
    """

    def __init__(self, session: Session):
        super().__init__(session, Agent)

    # ==========================================================
    # Identity
    # ==========================================================

    def get(
        self,
        agent_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> Agent | None:
        stmt = select(Agent).where(Agent.id == agent_id)
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return self.session.scalar(stmt)

    def get_by_uuid(
        self,
        agent_uuid: uuid.UUID,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> Agent | None:
        stmt = select(Agent).where(Agent.agent_uuid == agent_uuid)
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return self.session.scalar(stmt)

    def get_by_device(
        self,
        device_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> Agent | None:
        stmt = select(Agent).where(Agent.device_id == device_id)
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return self.session.scalar(stmt)

    def get_by_hostname(
        self,
        hostname: str,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> Agent | None:
        stmt = select(Agent).where(Agent.hostname == hostname)
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return self.session.scalar(stmt)

    # ==========================================================
    # Registration
    # ==========================================================

    def pending_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.registration_state == "pending")
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        stmt = stmt.order_by(Agent.created_at.asc())
        return list(self.session.scalars(stmt))

    def approved_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.registration_state == "approved")
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

    # ==========================================================
    # Status
    # ==========================================================

    def online_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.status == "online")
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

    def offline_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.status == "offline")
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

    def quarantined_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.quarantined.is_(True))
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

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
        now = datetime.now(timezone.utc)
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
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.update_available.is_(True))
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def revoke(self, agent: Agent, reason: str) -> Agent:
        agent.revoked = True
        agent.status = "revoked"
        agent.revocation_reason = reason
        agent.revoked_at = datetime.now(timezone.utc)
        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)
        return agent

    def quarantine(self, agent: Agent) -> Agent:
        agent.quarantined = True
        agent.status = "quarantined"
        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)
        return agent

    def restore(self, agent: Agent) -> Agent:
        agent.quarantined = False
        agent.revoked = False
        agent.status = "online"
        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)
        return agent
