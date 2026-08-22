"""Billing checkout: Stripe Checkout (card + PayPal when enabled in Stripe)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.dependencies import require_tenant_user
from app.core.config import settings
from app.database.session import get_db
from app.models.msp import Organization, TenantSubscription

router = APIRouter(prefix="/billing", tags=["Billing Checkout"])

DEFAULT_PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "Up to 25 endpoints — for small IT teams",
        "price_monthly": 49,
        "price_cents": 4900,
        "features": ["25 devices", "Remote access", "Ticketing", "Email support"],
    },
    {
        "code": "pro",
        "name": "Professional",
        "description": "Up to 250 endpoints — MSP ready",
        "price_monthly": 149,
        "price_cents": 14900,
        "features": ["250 devices", "Automation", "Alert engine", "Priority support"],
        "popular": True,
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Unlimited scale + dedicated support",
        "price_monthly": 399,
        "price_cents": 39900,
        "features": ["Unlimited devices", "SSO", "Custom SLA", "Dedicated CSM"],
    },
]


class CheckoutRequest(BaseModel):
    plan_code: str = Field(..., description="starter | pro | enterprise")
    email: EmailStr | None = None
    success_url: str | None = None
    cancel_url: str | None = None
    customer_name: str | None = None


def _stripe_secret() -> str:
    return (getattr(settings, "STRIPE_SECRET_KEY", None) or os.getenv("STRIPE_SECRET_KEY") or "").strip()


def _frontend_base() -> str:
    return (
        os.getenv("FRONTEND_URL")
        or os.getenv("NEXT_PUBLIC_APP_URL")
        or os.getenv("NEXT_PUBLIC_SITE_URL")
        or "https://bhudi.online"
    ).rstrip("/")


@router.get("/plans")
def list_checkout_plans(db: Session = Depends(get_db)):
    try:
        from app.services.msp_service import MspService

        svc = MspService(db)
        rows = svc.list_billing_plans() if hasattr(svc, "list_billing_plans") else []
        if rows:
            out = []
            for p in rows:
                out.append(
                    {
                        "code": getattr(p, "code", None) or str(getattr(p, "id", "")),
                        "name": getattr(p, "name", "Plan"),
                        "description": getattr(p, "description", "") or "",
                        "price_monthly": getattr(p, "price_monthly", None),
                        "price_cents": int(float(getattr(p, "price_monthly", 0) or 0) * 100),
                        "features": [],
                        "active": getattr(p, "active", True),
                    }
                )
            if out:
                return {"plans": out, "source": "db"}
    except Exception as exc:
        print(f"[billing] plans db fallback: {exc}")
    return {"plans": DEFAULT_PLANS, "source": "default"}


@router.get("/status")
def billing_status():
    key = _stripe_secret()
    return {
        "stripe_configured": bool(key),
        "paypal_via_stripe": True,
        "mode": "live"
        if key.startswith("sk_live")
        else ("test" if key.startswith("sk_test") else "unconfigured"),
        "message": (
            "Stripe is ready. PayPal appears in Checkout when enabled in your Stripe account."
            if key
            else "Set STRIPE_SECRET_KEY on the API to accept card and PayPal payments."
        ),
    }


def _stripe_form_post(path: str, fields: dict[str, str]) -> dict[str, Any]:
    secret = _stripe_secret()
    if not secret:
        raise HTTPException(503, "Stripe is not configured. Set STRIPE_SECRET_KEY on the backend.")
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/{path.lstrip('/')}",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
            msg = detail.get("error", {}).get("message") or body
        except Exception:
            msg = body
        raise HTTPException(e.code, f"Stripe error: {msg}") from e


def _organization_for_tenant(db: Session, tenant_id: UUID) -> Organization:
    org = db.query(Organization).filter(Organization.tenant_id == tenant_id).first()
    if org is None:
        raise HTTPException(409, "Billing organization is not configured for this tenant")
    return org


def _existing_subscription(db: Session, tenant_id: UUID) -> TenantSubscription | None:
    return (
        db.query(TenantSubscription)
        .filter(TenantSubscription.tenant_id == tenant_id)
        .first()
    )


@router.post("/checkout")
def create_checkout_session(
    body: CheckoutRequest,
    current_user=Depends(require_tenant_user),
    db: Session = Depends(get_db),
):
    plan = next((p for p in DEFAULT_PLANS if p["code"] == body.plan_code), None)
    if not plan:
        raise HTTPException(400, f"Unknown plan_code: {body.plan_code}")

    tenant_id = UUID(str(current_user.tenant_id))
    organization = _organization_for_tenant(db, tenant_id)
    subscription = _existing_subscription(db, tenant_id)

    base = _frontend_base()
    success = body.success_url or f"{base}/billing?success=1&plan={plan['code']}"
    cancel = body.cancel_url or f"{base}/billing?canceled=1"

    # Tenant/organization identity is resolved exclusively from the authenticated
    # server-side user. Browser-supplied tenant identifiers are never trusted.
    metadata = {
        "tenant_id": str(tenant_id),
        "organization_id": str(organization.id),
        "plan_code": plan["code"],
        "product": "bhudi",
    }

    fields: dict[str, str] = {
        "mode": "subscription",
        "success_url": success,
        "cancel_url": cancel,
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": str(plan["price_cents"]),
        "line_items[0][price_data][recurring][interval]": "month",
        "line_items[0][price_data][product_data][name]": f"Bhudi {plan['name']}",
        "line_items[0][price_data][product_data][description]": plan.get("description") or plan["name"],
        "line_items[0][quantity]": "1",
        "payment_method_types[0]": "card",
        "allow_promotion_codes": "true",
        "client_reference_id": str(tenant_id),
    }
    for key, value in metadata.items():
        fields[f"metadata[{key}]"] = value
        # Checkout Session metadata is not automatically copied to the Stripe
        # Subscription. Set subscription metadata explicitly so later
        # subscription/invoice webhooks retain the tenant binding.
        fields[f"subscription_data[metadata][{key}]"] = value

    # Use the authenticated account email, not a browser-provided email, for
    # billing identity. Existing Stripe customer IDs are reused when present.
    user_email = getattr(current_user, "email", None)
    if user_email:
        fields["customer_email"] = str(user_email)
    if subscription and subscription.external_customer_id:
        fields.pop("customer_email", None)
        fields["customer"] = str(subscription.external_customer_id)

    customer_name = getattr(current_user, "first_name", "") or ""
    last_name = getattr(current_user, "last_name", "") or ""
    if customer_name or last_name:
        fields["metadata[customer_name]"] = " ".join(
            part for part in (customer_name, last_name) if part
        )
    elif body.customer_name:
        fields["metadata[customer_name]"] = body.customer_name

    fields["payment_method_types[1]"] = "paypal"

    try:
        session = _stripe_form_post("checkout/sessions", fields)
    except HTTPException as e:
        if "paypal" in str(e.detail).lower() or e.status_code in (400, 402):
            fields.pop("payment_method_types[1]", None)
            session = _stripe_form_post("checkout/sessions", fields)
        else:
            raise

    return {
        "checkout_url": session.get("url"),
        "session_id": session.get("id"),
        "plan": plan,
        "mode": session.get("mode"),
        "tenant_id": str(tenant_id),
        "organization_id": str(organization.id),
    }


@router.post("/checkout/demo")
def demo_checkout(body: CheckoutRequest):
    plan = next((p for p in DEFAULT_PLANS if p["code"] == body.plan_code), None)
    if not plan:
        raise HTTPException(400, f"Unknown plan_code: {body.plan_code}")
    if _stripe_secret():
        return create_checkout_session(body)
    return {
        "demo": True,
        "message": "Stripe not configured — set STRIPE_SECRET_KEY for live card/PayPal checkout.",
        "plan": plan,
        "checkout_url": None,
    }
