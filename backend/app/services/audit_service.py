"""Best-effort audit trail writer for admin / privileged actions."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_trail import AuditTrail

logger = logging.getLogger(__name__)


def record_audit(
    db: Session,
    *,
    action: str,
    resource: str | None = None,
    details: dict[str, Any] | None = None,
    user_id: UUID | None = None,
    tenant_id: UUID | None = None,
    commit: bool = False,
) -> AuditTrail | None:
    """Write an AuditTrail row. Never raises — failures are logged only.

    When commit=False the caller is expected to commit the surrounding
    transaction (preferred so audit and business change share one txn).
    """
    try:
        entry = AuditTrail(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            details=details or {},
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
        return entry
    except Exception as exc:
        logger.warning("audit write failed action=%s resource=%s: %s", action, resource, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return None
