from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.agent_enrollment import AgentEnrollment
from app.models.tenant import Tenant
from app.services.entitlement_service import EntitlementService


class AgentEnrollmentService:
    """Creates and consumes reusable tenant-scoped agent enrollment credentials."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, tenant_id: uuid.UUID) -> tuple[str, AgentEnrollment]:
        raw = secrets.token_urlsafe(32)
        record = AgentEnrollment(tenant_id=tenant_id, token_hash=self._hash(raw), expires_at=None)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return raw, record

    def consume(self, token: str) -> AgentEnrollment:
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment credentials")

        record = self.db.scalar(
            select(AgentEnrollment).where(AgentEnrollment.token_hash == self._hash(token))
        )
        if record is None or record.revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment credentials")
        return record

    def enroll_agent(
        self,
        *,
        enrollment_secret: str,
        hostname: str,
        agent_version: str,
        platform: str | None,
        machine_guid: str | None,
    ) -> tuple[Agent, str, uuid.UUID]:
        enrollment = self.consume(enrollment_secret)
        tenant = self.db.get(Tenant, enrollment.tenant_id)
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment credentials")

        normalized_guid = (machine_guid or "").strip().lower() or None
        existing = None
        if normalized_guid:
            existing = self.db.scalar(
                select(Agent).where(Agent.machine_guid == normalized_guid)
            )
            if existing is not None and existing.tenant_id != tenant.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Machine is already enrolled")

        now = datetime.now(timezone.utc)
        agent_token = existing.enrollment_token if existing is not None and existing.enrollment_token else str(uuid.uuid4())

        if existing is None:
            existing = Agent(
                id=uuid.uuid4(),
                hostname=hostname,
                agent_version=agent_version,
                platform=platform,
                machine_guid=normalized_guid,
                tenant_id=tenant.id,
                enrollment_token=agent_token,
                registration_state="approved",
                approved=True,
                trusted=False,
                status="online",
                enabled=False,
                registered_at=now,
                last_seen=now,
                last_heartbeat=now,
            )
            self.db.add(existing)
        else:
            existing.hostname = hostname
            existing.agent_version = agent_version
            existing.platform = platform
            existing.machine_guid = normalized_guid
            existing.status = "online"
            existing.last_seen = now
            existing.last_heartbeat = now
            existing.revoked = False
            existing.enrollment_token = agent_token

        # Seat check: supportable only within paid device_limit
        EntitlementService(self.db).assign_supportable_on_enroll(tenant.id, existing)

        if enrollment.agent_id is None:
            enrollment.agent_id = existing.id
        self.db.add(enrollment)
        self.db.flush()
        self.db.commit()
        return existing, agent_token, tenant.id

    def revoke(self, tenant_id: uuid.UUID, token_id: uuid.UUID) -> AgentEnrollment:
        record = self.db.scalar(
            select(AgentEnrollment).where(
                AgentEnrollment.id == token_id,
                AgentEnrollment.tenant_id == tenant_id,
            )
        )
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment credential not found")
        record.revoked = True
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def mark_used(self, record: AgentEnrollment, agent_id: uuid.UUID) -> None:
        if record.agent_id is None:
            record.agent_id = agent_id
        self.db.add(record)
