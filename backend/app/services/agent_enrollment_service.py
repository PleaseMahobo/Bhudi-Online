from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_enrollment import AgentEnrollment


class AgentEnrollmentService:
    """Creates and consumes single-use tenant-bound agent enrollment tokens."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, tenant_id: uuid.UUID, *, ttl_minutes: int = 30) -> tuple[str, AgentEnrollment]:
        if ttl_minutes < 5 or ttl_minutes > 1440:
            raise ValueError("Enrollment token lifetime must be between 5 and 1440 minutes.")

        raw = secrets.token_urlsafe(32)
        record = AgentEnrollment(
            tenant_id=tenant_id,
            token_hash=self._hash(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )
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
        now = datetime.now(timezone.utc)
        if (
            record is None
            or record.revoked
            or record.used_at is not None
            or record.expires_at <= now
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment credentials")
        return record

    def mark_used(self, record: AgentEnrollment, agent_id: uuid.UUID) -> None:
        record.used_at = datetime.now(timezone.utc)
        record.agent_id = agent_id
        self.db.add(record)
        self.db.commit()
