from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.models.agent_enrollment import AgentEnrollment
from app.services.agent_enrollment_service import AgentEnrollmentService

router = APIRouter(prefix="/agent-enrollment", tags=["Agent Enrollment"])


@router.get("")
def list_enrollment_credentials(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    rows = db.scalars(
        select(AgentEnrollment)
        .where(AgentEnrollment.tenant_id == user.tenant_id)
        .order_by(AgentEnrollment.created_at.desc())
    ).all()
    return [
        {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "expires_at": None,
            "revoked": row.revoked,
            "created_at": row.created_at,
            "first_agent_id": str(row.agent_id) if row.agent_id else None,
            "reusable": True,
        }
        for row in rows
    ]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_enrollment_credential(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    AgentEnrollmentService(db).revoke(user.tenant_id, token_id)
    return None
