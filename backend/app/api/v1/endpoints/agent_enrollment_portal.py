from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.services.agent_enrollment_service import AgentEnrollmentService

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/enrollment-token")
def create_agent_enrollment_token(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    raw, record = AgentEnrollmentService(db).create(user.tenant_id)
    return {
        "token": raw,
        "expires_at": None,
        "tenant_id": str(user.tenant_id),
        "single_use": False,
        "reusable": True,
        "revocable": True,
    }
