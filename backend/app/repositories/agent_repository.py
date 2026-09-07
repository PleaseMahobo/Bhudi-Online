from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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

    def online_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        threshold_seconds: int = 180,
    ) -> list[Agent]:
        """Agents with a recent heartbeat/last_seen (PC on + agent service reachable)."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=threshold_seconds)
        stmt = select(Agent).where(
            Agent.revoked.is_(False),
            Agent.quarantined.is_(False),
            (
                (Agent.last_heartbeat.is_not(None) & (Agent.last_heartbeat >= cutoff))
                | (
                    Agent.last_heartbeat.is_(None)
                    & Agent.last_seen.is_not(None)
                    & (Agent.last_seen >= cutoff)
                )
            ),
        )
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

    def offline_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        threshold_seconds: int = 180,
    ) -> list[Agent]:
        """Agents with no recent heartbeat (PC off, network down, or agent stopped)."""
        online_ids = {
            a.id
            for a in self.online_agents(
                tenant_id=tenant_id, threshold_seconds=threshold_seconds
            )
        }
        stmt = select(Agent)
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        rows = list(self.session.scalars(stmt))
        return [a for a in rows if a.id not in online_ids]

    def quarantined_agents(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.quarantined.is_(True))
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

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

    def agents_needing_update(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.update_available.is_(True))
        if tenant_id is not None:
            stmt = stmt.where(Agent.tenant_id == tenant_id)
        return list(self.session.scalars(stmt))

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
