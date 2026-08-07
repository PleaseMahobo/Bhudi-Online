#!/usr/bin/env python3
"""Sign a Stripe webhook payload and optionally POST it to the local API.

Mirrors Stripe CLI / Dashboard signature format (t=...,v1=...).

Examples:
  python scripts/stripe_sign_payload.py --secret whsec_test --event invoice.paid --print-curl
  python scripts/stripe_sign_payload.py --secret whsec_test --event customer.subscription.updated --post
  python scripts/stripe_sign_payload.py --secret whsec_test --payload event.json --post

Exit codes:
  0 success
  1 usage / validation / HTTP error
  2 file or JSON error
  3 network / API unreachable
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
from pathlib import Path
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


def _load_event(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload:
        path = Path(args.payload)
        if not path.is_file():
            print(f"error: payload file not found: {path}", file=sys.stderr)
            raise SystemExit(2)
        try:
            raw = path.read_bytes()
        except OSError as e:
            print(f"error: cannot read {path}: {e}", file=sys.stderr)
            raise SystemExit(2) from e
        try:
            event = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError as e:
            print(f"error: payload is not valid UTF-8: {e}", file=sys.stderr)
            raise SystemExit(2) from e
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
            raise SystemExit(2) from e
        if not isinstance(event, dict):
            print("error: payload root must be a JSON object", file=sys.stderr)
            raise SystemExit(2)
        return event

    if args.event:
        return json.loads(json.dumps(FIXTURES[args.event]))  # deep copy

    print("error: provide --event or --payload", file=sys.stderr)
    raise SystemExit(1)


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
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout seconds (default 30)")
    args = parser.parse_args()

    if not args.secret.strip():
        print("error: --secret must not be empty", file=sys.stderr)
        return 1

    try:
        event = _load_event(args)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1

    obj = (event.get("data") or {}).get("object") or {}
    if not isinstance(obj, dict):
        print("error: data.object must be a JSON object when present", file=sys.stderr)
        return 2

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
        event["id"] = f"{event.get('id', 'evt_cli')}_{int(time.time())}"

    try:
        payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as e:
        print(f"error: cannot serialize event to JSON: {e}", file=sys.stderr)
        return 2

    header = sign(payload, args.secret)

    if args.print_curl or not args.post:
        body = payload.decode("utf-8").replace("'", "'\\''")
        print(
            f"curl -sS -X POST '{args.url}' \\\n"
            f"  -H 'Content-Type: application/json' \\\n"
            f"  -H 'Stripe-Signature: {header}' \\\n"
            f"  -d '{body}'"
        )

    if not args.post:
        return 0

    req = urllib.request.Request(
        args.url,
        data=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": header},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP {resp.status}")
            print(body)
            if resp.status >= 400:
                return 1
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"error: HTTP {e.code} from {args.url}", file=sys.stderr)
        if err_body:
            print(err_body, file=sys.stderr)
        if e.code == 400 and "signature" in err_body.lower():
            print(
                "hint: ensure STRIPE_ENABLED=true and STRIPE_WEBHOOK_SECRET matches --secret",
                file=sys.stderr,
            )
        return 1
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        print(f"error: API unreachable at {args.url}: {reason}", file=sys.stderr)
        print("hint: start the API (e.g. ./scripts/start_uvicorn.sh) and check --url", file=sys.stderr)
        return 3
    except TimeoutError:
        print(f"error: request timed out after {args.timeout}s: {args.url}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"error: network failure: {e}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130) from None
