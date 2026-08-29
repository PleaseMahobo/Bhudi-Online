"""Admin billing: inspect + force-activate tenant subscription (platform owner)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, _normalize_role
from app.database.session import get_db
from app.models.msp import BillingPlan, Organization, TenantSubscription
from app.models.user import User
from app.services.audit_service import record_audit
from app.services.entitlement_service import EntitlementService, PLAN_DEVICE_LIMITS
from app.services.msp_service import MspService

router = APIRouter(prefix="/billing/admin", tags=["Billing Admin"])

PLATFORM_OWNER_EMAILS = frozenset(
    {
        "security@bhudi.online",
        "security@cyberbastion.co.za",
    }
)

ADMIN_ROLES = frozenset(
    {
        "admin",
        "super_admin",
        "system_admin",
        "enterprise_admin",
        "msp_admin",
        "operator",
        "administrator",
    }
)


def _is_platform_admin(user: User) -> bool:
    email = (user.email or "").strip().lower()
    if email in PLATFORM_OWNER_EMAILS:
        return True
    role = _normalize_role(getattr(user, "role", None))
    if role in ADMIN_ROLES:
        return True
    try:
        for ur in getattr(user, "user_roles", None) or []:
            rname = getattr(getattr(ur, "role", None), "name", None) or getattr(ur, "name", None)
            if _normalize_role(rname) in ADMIN_ROLES:
                return True
    except Exception:
        pass
    return False


class ForceActivateRequest(BaseModel):
    tenant_id: UUID | None = Field(
        None, description="Target tenant. Defaults to caller's tenant."
    )
    plan_code: str = Field(
        "enterprise",
        description="starter | pro | professional | enterprise | admin",
    )
    email: str | None = None
    org_name: str | None = None


def _subscription_payload(sub: TenantSubscription | None) -> dict[str, Any] | None:
    if sub is None:
        return None
    return {
        "id": str(sub.id),
        "tenant_id": str(sub.tenant_id),
        "organization_id": str(sub.organization_id),
        "plan_id": str(sub.plan_id) if sub.plan_id else None,
        "status": sub.status,
        "seats": sub.seats,
        "device_limit": sub.device_limit,
        "current_period_start": sub.current_period_start.isoformat()
        if sub.current_period_start
        else None,
        "current_period_end": sub.current_period_end.isoformat()
        if sub.current_period_end
        else None,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "external_customer_id": sub.external_customer_id,
        "external_subscription_id": sub.external_subscription_id,
        "meta": sub.meta,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


@router.get("/subscription")
def inspect_subscription(
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Inspect subscription + entitlement for a tenant (defaults to caller)."""
    if not _is_platform_admin(user):
        raise HTTPException(403, "Platform admin required")

    tid = tenant_id or getattr(user, "tenant_id", None)
    if tid is None:
        raise HTTPException(400, "No tenant_id available")

    sub = (
        db.query(TenantSubscription)
        .filter(TenantSubscription.tenant_id == tid)
        .order_by(TenantSubscription.updated_at.desc())
        .first()
    )
    org = db.query(Organization).filter(Organization.tenant_id == tid).first()
    plans = db.query(BillingPlan).order_by(BillingPlan.code).all()
    ent = EntitlementService(db).get_entitlement(tid, user=user)

    record_audit(
        db,
        action="billing.admin.inspect",
        resource=f"tenant:{tid}",
        user_id=getattr(user, "id", None),
        tenant_id=tid,
        details={
            "actor_email": getattr(user, "email", None),
            "subscription_status": sub.status if sub else None,
            "entitlement_paid": ent.paid,
            "entitlement_plan": ent.plan_code,
        },
        commit=True,
    )

    return {
        "tenant_id": str(tid),
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "status": org.status,
        }
        if org
        else None,
        "subscription": _subscription_payload(sub),
        "entitlement": ent.to_dict(),
        "billing_plans_seeded": [
            {
                "id": str(p.id),
                "code": p.code,
                "name": p.name,
                "price": float(p.price or 0),
                "included_devices": p.included_devices,
                "active": p.active,
            }
            for p in plans
        ],
        "known_plan_limits": PLAN_DEVICE_LIMITS,
    }


@router.post("/subscription/activate")
def force_activate_subscription(
    body: ForceActivateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Force-activate (or upgrade) a tenant subscription — no Stripe required."""
    if not _is_platform_admin(user):
        raise HTTPException(403, "Platform admin required")

    tid = body.tenant_id or getattr(user, "tenant_id", None)
    if tid is None:
        raise HTTPException(400, "No tenant_id available")

    plan_code = (body.plan_code or "enterprise").strip().lower()
    if plan_code not in PLAN_DEVICE_LIMITS:
        raise HTTPException(
            400,
            f"Unknown plan_code '{plan_code}'. Known: {sorted(PLAN_DEVICE_LIMITS.keys())}",
        )

    # Snapshot prior state for audit
    prior = (
        db.query(TenantSubscription)
        .filter(TenantSubscription.tenant_id == tid)
        .first()
    )
    prior_status = prior.status if prior else None
    prior_plan = (prior.meta or {}).get("plan_code") if prior else None

    # Ensure catalog rows exist
    MspService(db).seed_default_plans()

    email = body.email or getattr(user, "email", None)
    org_name = body.org_name or email or "Bhudi Platform Owner"

    sub = EntitlementService(db).activate_subscription(
        tenant_id=tid,
        plan_code=plan_code,
        email=email,
        org_name=org_name,
    )

    # Link plan_id when a matching BillingPlan exists
    plan_row = db.query(BillingPlan).filter(BillingPlan.code == plan_code).first()
    if plan_row is None and plan_code == "pro":
        plan_row = db.query(BillingPlan).filter(BillingPlan.code == "professional").first()
    if plan_row is not None and sub.plan_id != plan_row.id:
        sub.plan_id = plan_row.id
        db.add(sub)
        db.commit()
        db.refresh(sub)

    ent = EntitlementService(db).get_entitlement(tid, user=user)

    record_audit(
        db,
        action="billing.admin.force_activate",
        resource=f"tenant:{tid}",
        user_id=getattr(user, "id", None),
        tenant_id=tid,
        details={
            "actor_email": getattr(user, "email", None),
            "plan_code": plan_code,
            "prior_status": prior_status,
            "prior_plan_code": prior_plan,
            "new_status": sub.status,
            "new_device_limit": sub.device_limit,
            "subscription_id": str(sub.id),
            "org_name": org_name,
        },
        commit=True,
    )

    return {
        "ok": True,
        "message": f"Subscription activated as '{plan_code}' for tenant {tid}",
        "subscription": _subscription_payload(sub),
        "entitlement": ent.to_dict(),
    }


@router.post("/plans/seed")
def seed_billing_plans(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Idempotent seed of default BillingPlan catalog rows."""
    if not _is_platform_admin(user):
        raise HTTPException(403, "Platform admin required")
    rows = MspService(db).seed_default_plans()

    record_audit(
        db,
        action="billing.admin.seed_plans",
        resource="billing_plans",
        user_id=getattr(user, "id", None),
        tenant_id=getattr(user, "tenant_id", None),
        details={
            "actor_email": getattr(user, "email", None),
            "plan_codes": [r.code for r in rows],
            "count": len(rows),
        },
        commit=True,
    )

    return {
        "ok": True,
        "count": len(rows),
        "plans": [
            {
                "id": str(r.id),
                "code": r.code,
                "name": r.name,
                "included_devices": r.included_devices,
                "price": float(r.price or 0),
                "active": r.active,
            }
            for r in rows
        ],
    }
