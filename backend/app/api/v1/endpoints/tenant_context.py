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
    tenant_id: UUID


@router.get("/tenants", status_code=200)
def list_tenant_contexts(
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    tenants = db.query(Tenant).order_by(Tenant.name.asc()).all()
    return [
        {"id": str(tenant.id), "name": tenant.name}
        for tenant in tenants
    ]


@router.post("", status_code=200)
def set_tenant_context(
    payload: TenantContextRequest,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    tenant = db.get(Tenant, payload.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    current_user.tenant_id = tenant.id
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {
        "user_id": str(current_user.id),
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
    }
