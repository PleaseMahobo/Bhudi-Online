"""Unit tests for Stripe webhook signature verification and CLI-oriented helpers.

Run:
  cd backend && pytest tests/test_stripe_webhook.py -q

These tests do not require Stripe CLI, network, or a live database.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.stripe_service import (
    DEFAULT_TOLERANCE_SECONDS,
    HANDLED_EVENTS,
    StripeBillingService,
    StripeSignatureError,
    verify_stripe_signature,
)


def _sign(payload: bytes, secret: str, *, timestamp: int | None = None) -> str:
    """Build a Stripe-Signature header the same way the Stripe CLI does."""
    ts = int(timestamp if timestamp is not None else time.time())
    signed = f"{ts}.".encode("utf-8") + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


SECRET = "whsec_test_secret_for_cli"


class TestVerifyStripeSignature:
    def test_valid_signature(self):
        payload = b'{"id":"evt_test","type":"invoice.paid"}'
        header = _sign(payload, SECRET)
        verify_stripe_signature(payload, header, SECRET)

    def test_missing_header(self):
        with pytest.raises(StripeSignatureError, match="Missing"):
            verify_stripe_signature(b"{}", None, SECRET)

    def test_empty_secret(self):
        with pytest.raises(StripeSignatureError, match="not configured"):
            verify_stripe_signature(b"{}", "t=1,v1=abc", "")

    def test_malformed_header(self):
        with pytest.raises(StripeSignatureError, match="Malformed"):
            verify_stripe_signature(b"{}", "nope", SECRET)

    def test_signature_mismatch(self):
        payload = b'{"id":"evt_x"}'
        header = _sign(payload, SECRET)
        with pytest.raises(StripeSignatureError, match="mismatch"):
            verify_stripe_signature(payload, header, "whsec_other")

    def test_timestamp_outside_tolerance(self):
        payload = b"{}"
        old = int(time.time()) - (DEFAULT_TOLERANCE_SECONDS + 60)
        header = _sign(payload, SECRET, timestamp=old)
        with pytest.raises(StripeSignatureError, match="tolerance"):
            verify_stripe_signature(payload, header, SECRET, tolerance=DEFAULT_TOLERANCE_SECONDS)

    def test_tolerance_zero_skips_skew_check(self):
        payload = b"{}"
        old = int(time.time()) - 10_000
        header = _sign(payload, SECRET, timestamp=old)
        verify_stripe_signature(payload, header, SECRET, tolerance=0)

    def test_multiple_v1_candidates(self):
        payload = b'{"ok":true}'
        ts = int(time.time())
        good = hmac.new(
            SECRET.encode("utf-8"),
            f"{ts}.".encode("utf-8") + payload,
            hashlib.sha256,
        ).hexdigest()
        header = f"t={ts},v1=deadbeef,v1={good}"
        verify_stripe_signature(payload, header, SECRET)


class TestStripeBillingServiceStatus:
    def test_status_shape(self):
        db = MagicMock()
        with patch("app.services.stripe_service.settings") as settings:
            settings.STRIPE_ENABLED = True
            settings.STRIPE_WEBHOOK_SECRET = SECRET
            settings.STRIPE_SECRET_KEY = "sk_test"
            settings.STRIPE_WEBHOOK_TOLERANCE = 300
            status = StripeBillingService(db).status()
        assert status["enabled"] is True
        assert status["webhook_secret_configured"] is True
        assert status["api_key_configured"] is True
        assert status["tolerance_seconds"] == 300
        assert set(status["handled_events"]) == set(HANDLED_EVENTS)


class TestProcessWebhookDisabled:
    def test_disabled_short_circuits(self):
        db = MagicMock()
        with patch("app.services.stripe_service.settings") as settings:
            settings.STRIPE_ENABLED = False
            result = StripeBillingService(db).process_webhook(b"{}", None)
        assert result == {"ok": False, "reason": "stripe_disabled"}
        db.query.assert_not_called()


class TestProcessWebhookHandlers:
    def _run(self, event: dict, *, secret: str = SECRET):
        payload = json.dumps(event).encode("utf-8")
        header = _sign(payload, secret)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.stripe_service.settings") as settings:
            settings.STRIPE_ENABLED = True
            settings.STRIPE_WEBHOOK_SECRET = secret
            settings.STRIPE_WEBHOOK_TOLERANCE = 300
            settings.STRIPE_STORE_PAYLOAD = False
            result = StripeBillingService(db).process_webhook(payload, header)
        return result, db

    def test_unknown_event_ignored(self):
        event = {
            "id": "evt_ignored_1",
            "type": "radar.early_fraud_warning.created",
            "livemode": False,
            "data": {"object": {}},
        }
        result, db = self._run(event)
        assert result["ok"] is True
        assert result["duplicate"] is False
        assert result["action"].startswith("ignored:")
        db.commit.assert_called()

    def test_invalid_json(self):
        payload = b"not-json"
        header = _sign(payload, SECRET)
        db = MagicMock()
        with patch("app.services.stripe_service.settings") as settings:
            settings.STRIPE_ENABLED = True
            settings.STRIPE_WEBHOOK_SECRET = SECRET
            settings.STRIPE_WEBHOOK_TOLERANCE = 300
            with pytest.raises(ValueError, match="Invalid JSON"):
                StripeBillingService(db).process_webhook(payload, header)

    def test_subscription_deleted_not_found(self):
        event = {
            "id": "evt_sub_del_1",
            "type": "customer.subscription.deleted",
            "livemode": False,
            "data": {
                "object": {
                    "id": "sub_missing",
                    "customer": "cus_missing",
                    "status": "canceled",
                }
            },
        }
        result, _db = self._run(event)
        assert result["ok"] is True
        assert "not_found" in result["action"]


class TestCliPayloadFixtures:
    """Fixtures shaped like Stripe CLI `stripe trigger` events."""

    def test_invoice_paid_fixture_signs(self):
        event = {
            "id": "evt_cli_invoice_paid",
            "object": "event",
            "type": "invoice.paid",
            "livemode": False,
            "data": {
                "object": {
                    "id": "in_test",
                    "object": "invoice",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "status": "paid",
                    "lines": {"data": [{"period": {"start": 1700000000, "end": 1702592000}}]},
                    "status_transitions": {"paid_at": 1700000100},
                }
            },
        }
        payload = json.dumps(event).encode("utf-8")
        header = _sign(payload, SECRET)
        verify_stripe_signature(payload, header, SECRET)
        assert "invoice.paid" in HANDLED_EVENTS
