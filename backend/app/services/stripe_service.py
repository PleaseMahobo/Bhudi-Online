"""Stripe webhook integration — signature verify + subscription sync.

Uses stdlib HMAC (no hard dependency on the stripe SDK). Outbound Stripe API
calls can be added later when STRIPE_SECRET_KEY is set and the optional
`stripe` package is installed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.msp import BillingPlan, Organization, StripeWebhookEvent, TenantSubscription

logger = logging.getLogger(__name__)

# Stripe subscription.status → internal status
_STATUS_MAP = {
    "trialing": "trialing",
    "active": "active",
    "past_due": "past_due",
    "canceled": "cancelled",
    "unpaid": "past_due",
    "paused": "paused",
    "incomplete": "trialing",
    "incomplete_expired": "cancelled",
}

DEFAULT_TOLERANCE_SECONDS = 300

HANDLED_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }
)


class StripeSignatureError(Exception):
    """Raised when Stripe-Signature header is missing or invalid."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ts_to_dt(ts: int | float | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def verify_stripe_signature(
    payload: bytes,
    sig_header: str | None,
    secret: str,
    *,
    tolerance: int = DEFAULT_TOLERANCE_SECONDS,
) -> None:
    """Verify Stripe-Signature header (t=...,v1=...).

    Raises StripeSignatureError on failure.
    """
    if not secret:
        raise StripeSignatureError("STRIPE_WEBHOOK_SECRET is not configured")
    if not sig_header:
        raise StripeSignatureError("Missing Stripe-Signature header")

    parts: dict[str, list[str]] = {}
    for item in sig_header.split(","):
        item = item.strip()
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        parts.setdefault(k.strip(), []).append(v.strip())

    if "t" not in parts or "v1" not in parts:
        raise StripeSignatureError("Malformed Stripe-Signature header")

    try:
        timestamp = int(parts["t"][0])
    except ValueError as e:
        raise StripeSignatureError("Invalid signature timestamp") from e

    if tolerance > 0 and abs(int(time.time()) - timestamp) > tolerance:
        raise StripeSignatureError("Signature timestamp outside tolerance")

    signed = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(
        secret.encode("utf-8"),
        signed,
        hashlib.sha256,
    ).hexdigest()

    candidates = parts["v1"]
    if not any(hmac.compare_digest(expected, c) for c in candidates):
        raise StripeSignatureError("Signature mismatch")


class StripeBillingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ----- Public entry ---------------------------------------------------

    def process_webhook(
        self,
        payload: bytes,
        sig_header: str | None,
    ) -> dict[str, Any]:
        """Verify signature, parse JSON, idempotently handle event."""
        if not settings.STRIPE_ENABLED:
            return {"ok": False, "reason": "stripe_disabled"}

        verify_stripe_signature(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
            tolerance=settings.STRIPE_WEBHOOK_TOLERANCE,
        )

        try:
            event = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e

        event_id = str(event.get("id") or "")
        event_type = str(event.get("type") or "")
        if not event_id or not event_type:
            raise ValueError("Event missing id or type")

        existing = (
            self.db.query(StripeWebhookEvent)
            .filter(StripeWebhookEvent.stripe_event_id == event_id)
            .first()
        )
        if existing and existing.status == "processed":
            return {
                "ok": True,
                "duplicate": True,
                "event_id": event_id,
                "type": event_type,
                "action": existing.action,
            }

        data_object = (event.get("data") or {}).get("object") or {}
        livemode = bool(event.get("livemode", False))

        row = existing or StripeWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            livemode=livemode,
            payload=event if settings.STRIPE_STORE_PAYLOAD else None,
            status="received",
        )
        if existing is None:
            self.db.add(row)
            self.db.flush()

        try:
            action = self._dispatch(event_type, data_object, event)
            row.status = "processed"
            row.action = action
            row.processed_at = _utcnow()
            row.error = None
            self.db.commit()
            return {
                "ok": True,
                "duplicate": False,
                "event_id": event_id,
                "type": event_type,
                "action": action,
            }
        except Exception as e:
            logger.exception("Stripe webhook handler failed for %s", event_id)
            row.status = "failed"
            row.error = str(e)[:2000]
            row.processed_at = _utcnow()
            self.db.commit()
            raise

    def status(self) -> dict[str, Any]:
        return {
            "enabled": settings.STRIPE_ENABLED,
            "webhook_secret_configured": bool(settings.STRIPE_WEBHOOK_SECRET),
            "api_key_configured": bool(settings.STRIPE_SECRET_KEY),
            "tolerance_seconds": settings.STRIPE_WEBHOOK_TOLERANCE,
            "handled_events": sorted(HANDLED_EVENTS),
        }

    # ----- Dispatch -------------------------------------------------------

    def _dispatch(
        self,
        event_type: str,
        obj: dict[str, Any],
        full_event: dict[str, Any],
    ) -> str:
        if event_type not in HANDLED_EVENTS:
            return f"ignored:{event_type}"

        if event_type == "checkout.session.completed":
            return self._on_checkout_completed(obj)
        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
        ):
            return self._on_subscription_upsert(obj)
        if event_type == "customer.subscription.deleted":
            return self._on_subscription_deleted(obj)
        if event_type == "invoice.paid":
            return self._on_invoice_paid(obj)
        if event_type == "invoice.payment_failed":
            return self._on_invoice_payment_failed(obj)
        return f"ignored:{event_type}"

    # ----- Handlers -------------------------------------------------------

    def _on_checkout_completed(self, session: dict[str, Any]) -> str:
        """Link customer/subscription after Checkout completes."""
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        metadata = session.get("metadata") or {}
        tenant_id = self._meta_uuid(metadata, "tenant_id")
        organization_id = self._meta_uuid(metadata, "organization_id")

        sub = None
        if tenant_id:
            sub = self._get_sub_by_tenant(tenant_id)
        if sub is None and organization_id:
            sub = self._get_sub_by_org(organization_id)
        if sub is None and customer_id:
            sub = self._get_sub_by_customer(str(customer_id))

        if sub is None:
            if organization_id:
                org = (
                    self.db.query(Organization)
                    .filter(Organization.id == organization_id)
                    .first()
                )
                if org:
                    sub = TenantSubscription(
                        tenant_id=org.tenant_id,
                        organization_id=org.id,
                        status="trialing",
                    )
                    self.db.add(sub)
                    self.db.flush()

        if sub is None:
            return "checkout:no_matching_subscription"

        if customer_id:
            sub.external_customer_id = str(customer_id)
        if subscription_id:
            sub.external_subscription_id = str(subscription_id)

        plan_code = metadata.get("plan_code")
        if plan_code:
            plan = (
                self.db.query(BillingPlan)
                .filter(BillingPlan.code == str(plan_code))
                .first()
            )
            if plan:
                sub.plan_id = plan.id

        mode = session.get("mode")
        if mode == "subscription" and subscription_id:
            sub.status = "active"
        sub.updated_at = _utcnow()
        meta = dict(sub.meta or {})
        meta["last_checkout_session_id"] = session.get("id")
        meta["stripe_checkout_mode"] = mode
        sub.meta = meta
        return f"checkout:linked:{sub.id}"

    def _on_subscription_upsert(self, stripe_sub: dict[str, Any]) -> str:
        external_sub_id = str(stripe_sub.get("id") or "")
        customer_id = stripe_sub.get("customer")
        metadata = stripe_sub.get("metadata") or {}
        status = _STATUS_MAP.get(str(stripe_sub.get("status") or ""), "active")

        sub = None
        if external_sub_id:
            sub = self._get_sub_by_external_sub(external_sub_id)
        if sub is None and customer_id:
            sub = self._get_sub_by_customer(str(customer_id))
        tenant_id = self._meta_uuid(metadata, "tenant_id")
        if sub is None and tenant_id:
            sub = self._get_sub_by_tenant(tenant_id)
        organization_id = self._meta_uuid(metadata, "organization_id")
        if sub is None and organization_id:
            sub = self._get_sub_by_org(organization_id)

        if sub is None and organization_id:
            org = (
                self.db.query(Organization)
                .filter(Organization.id == organization_id)
                .first()
            )
            if org:
                sub = TenantSubscription(
                    tenant_id=org.tenant_id,
                    organization_id=org.id,
                    status=status,
                )
                self.db.add(sub)
                self.db.flush()

        if sub is None:
            return f"subscription:orphan:{external_sub_id or 'unknown'}"

        if external_sub_id:
            sub.external_subscription_id = external_sub_id
        if customer_id:
            sub.external_customer_id = str(customer_id)
        sub.status = status
        sub.current_period_start = _ts_to_dt(stripe_sub.get("current_period_start"))
        sub.current_period_end = _ts_to_dt(stripe_sub.get("current_period_end"))
        sub.trial_ends_at = _ts_to_dt(stripe_sub.get("trial_end"))
        if status == "cancelled":
            sub.cancelled_at = _ts_to_dt(stripe_sub.get("canceled_at")) or _utcnow()
        else:
            sub.cancelled_at = None

        plan = self._resolve_plan_from_stripe_sub(stripe_sub, metadata)
        if plan:
            sub.plan_id = plan.id
            if plan.included_devices is not None and sub.device_limit is None:
                sub.device_limit = plan.included_devices
            if plan.included_users is not None and sub.seats is None:
                sub.seats = plan.included_users

        sub.updated_at = _utcnow()
        meta = dict(sub.meta or {})
        meta["stripe_status"] = stripe_sub.get("status")
        meta["stripe_cancel_at_period_end"] = stripe_sub.get("cancel_at_period_end")
        sub.meta = meta
        return f"subscription:upsert:{sub.id}:{status}"

    def _on_subscription_deleted(self, stripe_sub: dict[str, Any]) -> str:
        external_sub_id = str(stripe_sub.get("id") or "")
        sub = self._get_sub_by_external_sub(external_sub_id) if external_sub_id else None
        if sub is None:
            customer_id = stripe_sub.get("customer")
            if customer_id:
                sub = self._get_sub_by_customer(str(customer_id))
        if sub is None:
            return f"subscription:delete:not_found:{external_sub_id}"
        sub.status = "cancelled"
        sub.cancelled_at = _ts_to_dt(stripe_sub.get("canceled_at")) or _utcnow()
        sub.updated_at = _utcnow()
        return f"subscription:cancelled:{sub.id}"

    def _on_invoice_paid(self, invoice: dict[str, Any]) -> str:
        sub = self._sub_from_invoice(invoice)
        if sub is None:
            return "invoice.paid:no_subscription"
        if sub.status in ("past_due", "trialing", "paused"):
            sub.status = "active"
        lines = (invoice.get("lines") or {}).get("data") or []
        if lines:
            period = lines[0].get("period") or {}
            start = _ts_to_dt(period.get("start"))
            end = _ts_to_dt(period.get("end"))
            if start:
                sub.current_period_start = start
            if end:
                sub.current_period_end = end
        sub.updated_at = _utcnow()
        meta = dict(sub.meta or {})
        meta["last_invoice_id"] = invoice.get("id")
        meta["last_invoice_paid_at"] = invoice.get("status_transitions", {}).get(
            "paid_at"
        )
        sub.meta = meta
        return f"invoice.paid:{sub.id}"

    def _on_invoice_payment_failed(self, invoice: dict[str, Any]) -> str:
        sub = self._sub_from_invoice(invoice)
        if sub is None:
            return "invoice.payment_failed:no_subscription"
        sub.status = "past_due"
        sub.updated_at = _utcnow()
        meta = dict(sub.meta or {})
        meta["last_failed_invoice_id"] = invoice.get("id")
        meta["last_payment_failed_at"] = int(time.time())
        sub.meta = meta
        return f"invoice.payment_failed:{sub.id}"

    # ----- Lookups --------------------------------------------------------

    def _get_sub_by_tenant(self, tenant_id: UUID) -> TenantSubscription | None:
        return (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.tenant_id == tenant_id)
            .first()
        )

    def _get_sub_by_org(self, org_id: UUID) -> TenantSubscription | None:
        return (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.organization_id == org_id)
            .first()
        )

    def _get_sub_by_customer(self, customer_id: str) -> TenantSubscription | None:
        return (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.external_customer_id == customer_id)
            .first()
        )

    def _get_sub_by_external_sub(self, sub_id: str) -> TenantSubscription | None:
        return (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.external_subscription_id == sub_id)
            .first()
        )

    def _sub_from_invoice(self, invoice: dict[str, Any]) -> TenantSubscription | None:
        sub_id = invoice.get("subscription")
        if sub_id:
            found = self._get_sub_by_external_sub(str(sub_id))
            if found:
                return found
        customer_id = invoice.get("customer")
        if customer_id:
            return self._get_sub_by_customer(str(customer_id))
        return None

    def _resolve_plan_from_stripe_sub(
        self,
        stripe_sub: dict[str, Any],
        metadata: dict[str, Any],
    ) -> BillingPlan | None:
        plan_code = metadata.get("plan_code")
        if plan_code:
            plan = (
                self.db.query(BillingPlan)
                .filter(BillingPlan.code == str(plan_code))
                .first()
            )
            if plan:
                return plan

        items = (stripe_sub.get("items") or {}).get("data") or []
        for item in items:
            price = item.get("price") or {}
            price_id = price.get("id")
            if not price_id:
                continue
            plan = (
                self.db.query(BillingPlan)
                .filter(BillingPlan.stripe_price_id == str(price_id))
                .first()
            )
            if plan:
                return plan
        return None

    @staticmethod
    def _meta_uuid(metadata: dict[str, Any], key: str) -> UUID | None:
        raw = metadata.get(key)
        if not raw:
            return None
        try:
            return UUID(str(raw))
        except (ValueError, TypeError):
            return None
