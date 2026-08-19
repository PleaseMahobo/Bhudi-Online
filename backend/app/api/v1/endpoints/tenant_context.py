from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database.session import get_db
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/auth/tenant-context", tags=["Authentication"])


class TenantContextRequest(BaseModel):
    tenant_id: UUID | None = None


@router.post("", status_code=200)
def set_tenant_context(
    payload: TenantContextRequest,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    tenant = db.get(Tenant, payload.tenant_id) if payload.tenant_id else None
    if payload.tenant_id and tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    current_user.tenant_id = tenant.id if tenant else None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {
        "user_id": str(current_user.id),
        "tenant_id": str(tenant.id) if tenant else None,
        "tenant_name": tenant.name if tenant else None,
    }
