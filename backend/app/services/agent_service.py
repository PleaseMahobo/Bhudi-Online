from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository
from app.repositories.device_repository import DeviceRepository
from app.core.security import hash_password, verify_password


class AgentService:
    """Enterprise Agent Service with explicit tenant ownership enforcement."""

    def __init__(self, db: Session):
        self.db = db
        self.agents = AgentRepository(db)
        self.devices = DeviceRepository(db)

    def _scoped_agent(self, agent_id: uuid.UUID, tenant_id: uuid.UUID) -> Agent:
        agent = self.agents.get(agent_id, tenant_id=tenant_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found.")
        return agent

    def enroll(
        self,
        *,
        device_id: uuid.UUID,
        hostname: str,
        version: str,
        enrollment_secret: str,
        tenant_id: uuid.UUID | None = None,
    ) -> Agent:
        device = self.devices.get(device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found.")
        if device.tenant_id is None:
            raise HTTPException(status_code=409, detail="Device is not associated with a tenant.")
        if tenant_id is not None and device.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Device access denied.")

        owner_tenant_id = device.tenant_id
        if self.agents.get_by_device(device_id) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device already enrolled.")

        agent = Agent()
        agent.agent_uuid = uuid.uuid4()
        agent.device_id = device_id
        agent.tenant_id = owner_tenant_id
        agent.hostname = hostname
        agent.agent_version = version
        agent.registration_state = "pending"
        agent.enrollment_secret_hash = hash_password(enrollment_secret)

        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def approve(self, agent_id: uuid.UUID, approver: uuid.UUID, tenant_id: uuid.UUID) -> Agent:
        agent = self._scoped_agent(agent_id, tenant_id)
        agent.registration_state = "approved"
        agent.approved_at = datetime.now(timezone.utc)
        agent.approved_by = approver
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def authenticate(self, *, agent_uuid: uuid.UUID, enrollment_secret: str) -> Agent:
        agent = self.agents.get_by_uuid(agent_uuid)
        if not agent or not agent.tenant_id:
            raise HTTPException(status_code=401, detail="Authentication failed.")
        if agent.revoked:
            raise HTTPException(status_code=403, detail="Agent revoked.")
        if not agent.enrollment_secret_hash or not verify_password(enrollment_secret, agent.enrollment_secret_hash):
            raise HTTPException(status_code=401, detail="Authentication failed.")
        return agent

    def heartbeat(self, *, agent_uuid: uuid.UUID, ip_address: str | None, username: str | None) -> Agent:
        agent = self.agents.get_by_uuid(agent_uuid)
        if not agent or not agent.tenant_id:
            raise HTTPException(status_code=401, detail="Authentication failed.")
        return self.agents.heartbeat(agent, ip_address=ip_address, username=username)

    def mark_update_available(self, agent_id: uuid.UUID, target_version: str, tenant_id: uuid.UUID) -> Agent:
        agent = self._scoped_agent(agent_id, tenant_id)
        agent.update_available = True
        agent.target_version = target_version
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def complete_update(self, *, agent_uuid: uuid.UUID, installed_version: str) -> Agent:
        agent = self.agents.get_by_uuid(agent_uuid)
        if not agent or not agent.tenant_id:
            raise HTTPException(status_code=401, detail="Authentication failed.")
        agent.agent_version = installed_version
        agent.last_update = datetime.now(timezone.utc)
        agent.update_available = False
        agent.target_version = None
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def quarantine(self, agent_id: uuid.UUID, tenant_id: uuid.UUID) -> Agent:
        return self.agents.quarantine(self._scoped_agent(agent_id, tenant_id))

    def revoke(self, *, agent_id: uuid.UUID, reason: str, tenant_id: uuid.UUID) -> Agent:
        return self.agents.revoke(self._scoped_agent(agent_id, tenant_id), reason)

    def restore(self, agent_id: uuid.UUID, tenant_id: uuid.UUID) -> Agent:
        return self.agents.restore(self._scoped_agent(agent_id, tenant_id))
