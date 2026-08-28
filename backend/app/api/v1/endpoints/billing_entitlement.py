"""Billing entitlement API for frontend paywall + agent download gate."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.services.entitlement_service import EntitlementService

router = APIRouter(prefix="/billing", tags=["Billing Entitlement"])


@router.get("/entitlement")
def get_entitlement(db: Session = Depends(get_db), user=Depends(current_tenant_user)):
    ent = EntitlementService(db).get_entitlement(getattr(user, "tenant_id", None))
    return ent.to_dict()
