"""One-shot heal for platform owner accounts (tenant + enterprise_admin + download)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, ensure_user_has_tenant, _normalize_role
from app.database.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.services.entitlement_service import EntitlementService

router = APIRouter(prefix="/auth", tags=["Authentication"])

PLATFORM_OWNER_EMAILS = frozenset(
    {
        "security@bhudi.online",
        "security@cyberbastion.co.za",
    }
)


@router.post("/platform-heal")
def platform_heal(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Promote caller to enterprise_admin, ensure tenant, unlock agent download.

    Allowed for:
      - security@bhudi.online (and related owner emails)
      - any user already holding an admin-family role string
    """
    email = (user.email or "").strip().lower()
    role_norm = _normalize_role(getattr(user, "role", None))
    allowed = email in PLATFORM_OWNER_EMAILS or role_norm in {
        "admin",
        "super_admin",
        "system_admin",
        "enterprise_admin",
        "msp_admin",
        "operator",
        "administrator",
    }
    if not allowed:
        raise HTTPException(status_code=403, detail="Not permitted to run platform heal")

    # 1) Highest role on user column
    user.role = "enterprise_admin"
    user.active = True
    db.add(user)
    db.flush()

    # 2) Ensure enterprise_admin exists in roles table + assignment
    ea = db.query(Role).filter(Role.name == "enterprise_admin").first()
    if ea is None:
        ea = Role(
            name="enterprise_admin",
            description="Highest platform role — full control of Bhudi Online",
            system=True,
        )
        db.add(ea)
        db.flush()

    # Drop legacy role links for this user; keep only enterprise_admin
    db.query(UserRole).filter(UserRole.user_id == user.id).delete()
    db.add(UserRole(user_id=user.id, role_id=ea.id))
    db.flush()

    # 3) Tenant
    user = ensure_user_has_tenant(user, db)

    # 4) Entitlement / download seats
    ent_svc = EntitlementService(db)
    ent_svc.require_download_allowed(user.tenant_id, user=user)
    ent = ent_svc.get_entitlement(user.tenant_id, user=user)

    db.commit()
    db.refresh(user)

    return {
        "ok": True,
        "email": user.email,
        "role": user.role,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "entitlement": ent.to_dict(),
        "message": "enterprise_admin set; tenant provisioned; agent download unlocked",
    }
