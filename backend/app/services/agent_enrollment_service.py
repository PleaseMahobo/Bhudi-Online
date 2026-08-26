from __future__ import annotations

import hashlib
import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_enrollment import AgentEnrollment


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
        # Preserve first-use audit linkage without invalidating a reusable credential.
        if record.agent_id is None:
            record.agent_id = agent_id
            self.db.add(record)
            self.db.commit()
