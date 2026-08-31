"""Subscription entitlement: paid access, agent download, supportable device seats."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.msp import Organization, TenantSubscription

PLAN_DEVICE_LIMITS: dict[str, int] = {
    "starter": 1,
    "personal": 1,
    "pro": 250,
    "professional": 250,
    "enterprise": 1_000_000,
    "admin": 10_000,
}

ACTIVE_STATUSES = frozenset({"active", "trialing"})

# Platform operators may download/install without a Stripe subscription.
# Matched after normalizing: lower-case, spaces/hyphens -> underscore.
ADMIN_DOWNLOAD_ROLES = frozenset(
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
ADMIN_DEVICE_LIMIT = 10_000


@dataclass
class Entitlement:
    paid: bool
    status: str
    plan_code: str | None
    device_limit: int
    supportable_count: int
    seats_remaining: int
    can_download_agent: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "paid": self.paid,
            "status": self.status,
            "plan_code": self.plan_code,
            "device_limit": self.device_limit,
            "supportable_count": self.supportable_count,
            "seats_remaining": self.seats_remaining,
            "can_download_agent": self.can_download_agent,
        }


def _normalize_role(name: str | None) -> str:
    """system admin / System-Admin / system_admin -> system_admin"""
    if not name:
        return ""
    return (
        str(name)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
    )


def _user_is_admin(user: Any | None) -> bool:
    if user is None:
        return False
    role = _normalize_role(getattr(user, "role", None))
    if role in ADMIN_DOWNLOAD_ROLES:
        return True
    # Some installs store roles only on the user_roles relation.
    try:
        for ur in getattr(user, "user_roles", None) or []:
            rname = getattr(getattr(ur, "role", None), "name", None) or getattr(ur, "name", None)
            if _normalize_role(rname) in ADMIN_DOWNLOAD_ROLES:
                return True
    except Exception:
        pass
    return False


class EntitlementService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _subscription_for_tenant(self, tenant_id: UUID) -> TenantSubscription | None:
        return (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.tenant_id == tenant_id)
            .order_by(TenantSubscription.updated_at.desc())
            .first()
        )

    def _count_supportable(self, tenant_id: UUID) -> int:
        q = select(func.count()).select_from(Agent).where(
            Agent.tenant_id == tenant_id,
            Agent.trusted.is_(True),
        )
        return int(self.db.scalar(q) or 0)

    def get_entitlement(self, tenant_id: UUID | None, user: Any | None = None) -> Entitlement:
        if tenant_id is None:
            if _user_is_admin(user):
                return Entitlement(
                    paid=True,
                    status="admin",
                    plan_code="admin",
                    device_limit=ADMIN_DEVICE_LIMIT,
                    supportable_count=0,
                    seats_remaining=ADMIN_DEVICE_LIMIT,
                    can_download_agent=True,
                )
            return Entitlement(
                paid=False,
                status="none",
                plan_code=None,
                device_limit=0,
                supportable_count=0,
                seats_remaining=0,
                can_download_agent=False,
            )

        supportable = self._count_supportable(tenant_id)

        # Platform admin / operator always allowed to download and enroll.
        if _user_is_admin(user):
            remaining = max(0, ADMIN_DEVICE_LIMIT - supportable)
            return Entitlement(
                paid=True,
                status="admin",
                plan_code="admin",
                device_limit=ADMIN_DEVICE_LIMIT,
                supportable_count=supportable,
                seats_remaining=remaining,
                can_download_agent=True,
            )

        sub = self._subscription_for_tenant(tenant_id)
        if sub is None:
            return Entitlement(
                paid=False,
                status="none",
                plan_code=None,
                device_limit=0,
                supportable_count=supportable,
                seats_remaining=0,
                can_download_agent=False,
            )

        status_s = (getattr(sub, "status", None) or "").lower()
        paid = status_s in ACTIVE_STATUSES
        plan_code = None
        limit = getattr(sub, "device_limit", None)
        meta = dict(getattr(sub, "meta", None) or {})
        plan_code = meta.get("plan_code")
        if limit is None:
            plan = getattr(sub, "plan", None)
            if plan is not None:
                plan_code = getattr(plan, "code", None) or plan_code
                included = getattr(plan, "included_devices", None)
                if included is not None:
                    limit = int(included)
            if limit is None and plan_code:
                limit = PLAN_DEVICE_LIMITS.get(str(plan_code).lower(), 0)
            if limit is None:
                limit = PLAN_DEVICE_LIMITS.get(str(plan_code or "").lower(), 0 if not paid else 1)

        limit = int(limit or 0)
        if not paid:
            limit = 0

        remaining = max(0, limit - supportable)

        return Entitlement(
            paid=paid,
            status=status_s or "none",
            plan_code=str(plan_code) if plan_code else None,
            device_limit=limit,
            supportable_count=supportable,
            seats_remaining=remaining,
            can_download_agent=paid,
        )

    def require_download_allowed(self, tenant_id: UUID | None, user: Any | None = None) -> Entitlement:
        """Gate agent download / enrollment token creation.

        Platform admins / owners always get access. On first use we also
        persist an active 'enterprise' subscription so later enroll calls
        (which have no user context) still see seats available.
        """
        ent = self.get_entitlement(tenant_id, user=user)
        if not ent.can_download_agent:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "subscription_required",
                    "message": (
                        "An active subscription is required to download the agent. "
                        "Subscribe under Billing, then return here to download."
                    ),
                    "billing_path": "/billing",
                },
            )

        # Auto-provision entitlement for platform owner / admin on first use.
        # Ensures enrollment tokens work during development without Stripe.
        if _user_is_admin(user) and tenant_id is not None:
            sub = self._subscription_for_tenant(tenant_id)
            status_s = (getattr(sub, "status", None) or "").lower() if sub else ""
            if sub is None or status_s not in ACTIVE_STATUSES:
                email = getattr(user, "email", None)
                self.activate_subscription(
                    tenant_id=tenant_id,
                    plan_code="enterprise",  # high device limit for owner/dev
                    email=email,
                    org_name=email or "Bhudi Platform Owner",
                )
                # Refresh so callers see the new limits immediately
                ent = self.get_entitlement(tenant_id, user=user)
        return ent

    def assign_supportable_on_enroll(self, tenant_id: UUID, agent: Agent) -> bool:
        ent = self.get_entitlement(tenant_id)
        if getattr(agent, "trusted", False):
            return True

        if ent.paid and ent.seats_remaining > 0:
            agent.trusted = True
            agent.approved = True
            agent.enabled = True
            agent.registration_state = "approved"
            return True

        agent.trusted = False
        agent.approved = True
        agent.enabled = False
        agent.registration_state = "unlicensed"
        return False

    def _ensure_organization(self, tenant_id: UUID, name: str | None = None) -> Organization:
        org = (
            self.db.query(Organization)
            .filter(Organization.tenant_id == tenant_id)
            .first()
        )
        if org:
            return org
        slug = f"t-{str(tenant_id).replace('-', '')[:16]}"
        org = Organization(
            id=uuid4(),
            tenant_id=tenant_id,
            name=(name or "Bhudi Customer")[:255],
            slug=slug,
            org_type="client",
            status="active",
        )
        self.db.add(org)
        self.db.flush()
        return org

    def activate_subscription(
        self,
        *,
        tenant_id: UUID,
        plan_code: str,
        email: str | None = None,
        stripe_session_id: str | None = None,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        org_name: str | None = None,
    ) -> TenantSubscription:
        """Create or update TenantSubscription as active and set device_limit from plan."""
        limit = PLAN_DEVICE_LIMITS.get(plan_code.lower(), 1)
        org = self._ensure_organization(tenant_id, name=org_name or email)
        sub = self._subscription_for_tenant(tenant_id)
        now = datetime.now(timezone.utc)
        if sub is None:
            sub = TenantSubscription(
                id=uuid4(),
                tenant_id=tenant_id,
                organization_id=org.id,
                status="active",
                device_limit=limit,
                seats=limit,
                current_period_start=now,
                meta={
                    "plan_code": plan_code,
                    "activated_at": now.isoformat(),
                    "last_checkout_session_id": stripe_session_id,
                    "email": email,
                },
            )
            self.db.add(sub)
        else:
            sub.status = "active"
            sub.device_limit = limit
            sub.seats = limit
            sub.cancelled_at = None
            sub.updated_at = now
            meta = dict(sub.meta or {})
            meta["plan_code"] = plan_code
            meta["activated_at"] = now.isoformat()
            if stripe_session_id:
                meta["last_checkout_session_id"] = stripe_session_id
            if email:
                meta["email"] = email
            sub.meta = meta
        if stripe_customer_id:
            sub.external_customer_id = str(stripe_customer_id)
        if stripe_subscription_id:
            sub.external_subscription_id = str(stripe_subscription_id)
        self.db.commit()
        self.db.refresh(sub)
        return sub
