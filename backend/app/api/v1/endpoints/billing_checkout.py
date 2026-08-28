"""Billing checkout: Stripe Checkout with tenant metadata + immediate entitlement activate."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.services.entitlement_service import EntitlementService, PLAN_DEVICE_LIMITS

router = APIRouter(prefix="/billing", tags=["Billing Checkout"])

DEFAULT_PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "1 managed endpoint — personal / single device",
        "price_monthly": 49,
        "price_cents": 4900,
        "device_limit": 1,
        "features": ["1 device", "Remote access", "Ticketing", "Email support"],
    },
    {
        "code": "pro",
        "name": "Professional",
        "description": "Up to 250 endpoints — organisations & MSP",
        "price_monthly": 149,
        "price_cents": 14900,
        "device_limit": 250,
        "features": ["250 devices", "Org enroll", "Automation", "Priority support"],
        "popular": True,
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Unlimited scale + dedicated support",
        "price_monthly": 399,
        "price_cents": 39900,
        "device_limit": 1_000_000,
        "features": ["Unlimited devices", "SSO", "Custom SLA", "Dedicated CSM"],
    },
]


class CheckoutRequest(BaseModel):
    plan_code: str = Field(..., description="starter | pro | enterprise")
    email: EmailStr | None = None
    success_url: str | None = None
    cancel_url: str | None = None
    customer_name: str | None = None


class ConfirmCheckoutRequest(BaseModel):
    session_id: str | None = None
    plan_code: str | None = None


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
                code = getattr(p, "code", None) or str(getattr(p, "id", ""))
                out.append(
                    {
                        "code": code,
                        "name": getattr(p, "name", "Plan"),
                        "description": getattr(p, "description", "") or "",
                        "price_monthly": getattr(p, "price_monthly", None) or float(getattr(p, "price", 0) or 0),
                        "price_cents": int(float(getattr(p, "price_monthly", None) or getattr(p, "price", 0) or 0) * 100),
                        "device_limit": getattr(p, "included_devices", None)
                        or PLAN_DEVICE_LIMITS.get(str(code).lower(), 1),
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


def _stripe_get(path: str) -> dict[str, Any]:
    secret = _stripe_secret()
    if not secret:
        raise HTTPException(503, "Stripe is not configured.")
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/{path.lstrip('/')}",
        method="GET",
        headers={"Authorization": f"Bearer {secret}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise HTTPException(e.code, f"Stripe error: {body}") from e


@router.post("/checkout")
def create_checkout_session(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    plan = next((p for p in DEFAULT_PLANS if p["code"] == body.plan_code), None)
    if not plan:
        raise HTTPException(400, f"Unknown plan_code: {body.plan_code}")

    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(400, "User has no tenant — cannot bind subscription")

    base = _frontend_base()
    success = body.success_url or (
        f"{base}/billing?success=1&plan={plan['code']}"
        f"&session_id={{CHECKOUT_SESSION_ID}}"
    )
    cancel = body.cancel_url or f"{base}/billing?canceled=1"

    email = str(body.email or getattr(user, "email", None) or "")

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
        "metadata[plan_code]": plan["code"],
        "metadata[product]": "bhudi",
        "metadata[tenant_id]": str(tenant_id),
        "metadata[user_id]": str(getattr(user, "id", "")),
        "subscription_data[metadata][tenant_id]": str(tenant_id),
        "subscription_data[metadata][plan_code]": plan["code"],
    }
    if email:
        fields["customer_email"] = email
        fields["metadata[email]"] = email
    if body.customer_name:
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
    }


@router.post("/checkout/confirm")
def confirm_checkout(
    body: ConfirmCheckoutRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    """Activate entitlement immediately after Stripe success redirect (before webhook)."""
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(400, "User has no tenant")

    plan_code = (body.plan_code or "starter").lower()
    session_id = body.session_id
    stripe_customer = None
    stripe_sub = None

    if session_id and _stripe_secret():
        try:
            session = _stripe_get(f"checkout/sessions/{session_id}")
            meta = session.get("metadata") or {}
            # Prefer metadata tenant; must match current user
            meta_tenant = meta.get("tenant_id")
            if meta_tenant and str(meta_tenant) != str(tenant_id):
                raise HTTPException(403, "Checkout session does not belong to this account")
            plan_code = str(meta.get("plan_code") or plan_code).lower()
            stripe_customer = session.get("customer")
            stripe_sub = session.get("subscription")
            payment_status = session.get("payment_status") or session.get("status")
            if payment_status not in ("paid", "complete", "complete", "no_payment_required"):
                # still allow activate if session completed
                if session.get("status") != "complete":
                    raise HTTPException(402, f"Checkout not complete yet ({payment_status})")
        except HTTPException:
            raise
        except Exception as exc:
            print(f"[billing] confirm session lookup: {exc}")

    if plan_code not in PLAN_DEVICE_LIMITS and plan_code not in {p["code"] for p in DEFAULT_PLANS}:
        plan_code = "starter"

    try:
        sub = EntitlementService(db).activate_subscription(
            tenant_id=tenant_id,
            plan_code=plan_code,
            email=getattr(user, "email", None),
            stripe_session_id=session_id,
            stripe_customer_id=str(stripe_customer) if stripe_customer else None,
            stripe_subscription_id=str(stripe_sub) if stripe_sub else None,
            org_name=getattr(user, "email", None),
        )
    except Exception as exc:
        raise HTTPException(500, f"Failed to activate subscription: {exc}") from exp

    ent = EntitlementService(db).get_entitlement(tenant_id)
    return {
        "ok": True,
        "subscription_id": str(sub.id),
        "status": sub.status,
        "entitlement": ent.to_dict(),
    }


@router.post("/checkout/demo")
def demo_checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    plan = next((p for p in DEFAULT_PLANS if p["code"] == body.plan_code), None)
    if not plan:
        raise HTTPException(400, f"Unknown plan_code: {body.plan_code}")
    if _stripe_secret():
        return create_checkout_session(body, db=db, user=user)
    # Dev path: activate without Stripe
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id:
        EntitlementService(db).activate_subscription(
            tenant_id=tenant_id,
            plan_code=plan["code"],
            email=getattr(user, "email", None),
        )
    return {
        "demo": True,
        "message": "Stripe not configured — activated local entitlement for development.",
        "plan": plan,
        "checkout_url": None,
        "entitlement": EntitlementService(db).get_entitlement(tenant_id).to_dict() if tenant_id else None,
    }
