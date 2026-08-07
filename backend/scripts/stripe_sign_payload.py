#!/usr/bin/env python3
"""Sign a Stripe webhook payload and optionally POST it to the local API.

Mirrors Stripe CLI / Dashboard signature format (t=...,v1=...).

Examples:
  python scripts/stripe_sign_payload.py --secret whsec_test --event invoice.paid --print-curl
  python scripts/stripe_sign_payload.py --secret whsec_test --event customer.subscription.updated --post
  python scripts/stripe_sign_payload.py --secret whsec_test --payload event.json --post
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


FIXTURES: dict[str, dict[str, Any]] = {
    "invoice.paid": {
        "id": "evt_cli_invoice_paid",
        "object": "event",
        "type": "invoice.paid",
        "livemode": False,
        "data": {
            "object": {
                "id": "in_test_cli",
                "object": "invoice",
                "customer": "cus_test_cli",
                "subscription": "sub_test_cli",
                "status": "paid",
                "lines": {"data": [{"period": {"start": 1700000000, "end": 1702592000}}]},
                "status_transitions": {"paid_at": 1700000100},
            }
        },
    },
    "invoice.payment_failed": {
        "id": "evt_cli_invoice_failed",
        "object": "event",
        "type": "invoice.payment_failed",
        "livemode": False,
        "data": {
            "object": {
                "id": "in_test_fail",
                "object": "invoice",
                "customer": "cus_test_cli",
                "subscription": "sub_test_cli",
                "status": "open",
            }
        },
    },
    "customer.subscription.updated": {
        "id": "evt_cli_sub_updated",
        "object": "event",
        "type": "customer.subscription.updated",
        "livemode": False,
        "data": {
            "object": {
                "id": "sub_test_cli",
                "object": "subscription",
                "customer": "cus_test_cli",
                "status": "active",
                "current_period_start": 1700000000,
                "current_period_end": 1702592000,
                "cancel_at_period_end": False,
                "metadata": {},
                "items": {"data": []},
            }
        },
    },
    "customer.subscription.deleted": {
        "id": "evt_cli_sub_deleted",
        "object": "event",
        "type": "customer.subscription.deleted",
        "livemode": False,
        "data": {
            "object": {
                "id": "sub_test_cli",
                "object": "subscription",
                "customer": "cus_test_cli",
                "status": "canceled",
                "canceled_at": 1700001000,
            }
        },
    },
    "customer.subscription.created": {
        "id": "evt_cli_sub_created",
        "object": "event",
        "type": "customer.subscription.created",
        "livemode": False,
        "data": {
            "object": {
                "id": "sub_test_cli_new",
                "object": "subscription",
                "customer": "cus_test_cli",
                "status": "trialing",
                "trial_end": 1700604800,
                "current_period_start": 1700000000,
                "current_period_end": 1702592000,
                "metadata": {},
                "items": {"data": []},
            }
        },
    },
    "checkout.session.completed": {
        "id": "evt_cli_checkout",
        "object": "event",
        "type": "checkout.session.completed",
        "livemode": False,
        "data": {
            "object": {
                "id": "cs_test_cli",
                "object": "checkout.session",
                "customer": "cus_test_cli",
                "subscription": "sub_test_cli",
                "mode": "subscription",
                "metadata": {},
            }
        },
    },
}


def sign(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    ts = int(timestamp if timestamp is not None else time.time())
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{ts}.".encode("utf-8") + payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={ts},v1={digest}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign / post Stripe webhook test payloads")
    parser.add_argument("--secret", required=True, help="Webhook signing secret (whsec_...)")
    parser.add_argument("--event", choices=sorted(FIXTURES.keys()), help="Built-in fixture event type")
    parser.add_argument("--payload", help="Path to JSON event file (overrides --event)")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/api/v1/msp/billing/stripe/webhook",
        help="Webhook endpoint URL",
    )
    parser.add_argument("--post", action="store_true", help="POST the signed payload")
    parser.add_argument("--print-curl", action="store_true", help="Print a curl command")
    parser.add_argument("--tenant-id", default="", help="Inject metadata.tenant_id")
    parser.add_argument("--organization-id", default="", help="Inject metadata.organization_id")
    parser.add_argument("--plan-code", default="", help="Inject metadata.plan_code")
    args = parser.parse_args()

    if args.payload:
        with open(args.payload, "rb") as f:
            payload = f.read()
        event = json.loads(payload.decode("utf-8"))
    elif args.event:
        event = json.loads(json.dumps(FIXTURES[args.event]))
    else:
        parser.error("Provide --event or --payload")

    obj = (event.get("data") or {}).get("object") or {}
    meta = dict(obj.get("metadata") or {})
    if args.tenant_id:
        meta["tenant_id"] = args.tenant_id
    if args.organization_id:
        meta["organization_id"] = args.organization_id
    if args.plan_code:
        meta["plan_code"] = args.plan_code
    if meta:
        obj["metadata"] = meta
        event.setdefault("data", {})["object"] = obj

    if args.event and not args.payload:
        event["id"] = f"{event['id']}_{int(time.time())}"

    payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
    header = sign(payload, args.secret)

    if args.print_curl or not args.post:
        body = payload.decode("utf-8").replace("'", "'\\''")
        print(
            f"curl -sS -X POST '{args.url}' \\\n"
            f"  -H 'Content-Type: application/json' \\\n"
            f"  -H 'Stripe-Signature: {header}' \\\n"
            f"  -d '{body}'"
        )

    if args.post:
        req = urllib.request.Request(
            args.url,
            data=payload,
            headers={"Content-Type": "application/json", "Stripe-Signature": header},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                print(f"HTTP {resp.status}")
                print(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}", file=sys.stderr)
            print(e.read().decode("utf-8"), file=sys.stderr)
            return 1
        except urllib.error.URLError as e:
            print(f"Request failed: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
