# Stripe CLI testing (MSP billing webhooks)

## Prerequisites

1. [Stripe CLI](https://stripe.com/docs/stripe-cli) installed and `stripe login`
2. Backend API running (e.g. `./scripts/start_uvicorn.sh` or uvicorn)
3. `alembic upgrade head` applied (includes `stripe_webhook_events`)
4. Env:

```bash
STRIPE_ENABLED=true
STRIPE_WEBHOOK_SECRET=whsec_...   # from `stripe listen` output
```

## Quick path (Stripe CLI)

```bash
# Terminal A — API
export STRIPE_ENABLED=true
export STRIPE_WEBHOOK_SECRET=whsec_placeholder
./scripts/start_uvicorn.sh

# Terminal B — forward webhooks
./scripts/stripe_cli_test.sh listen
# Copy printed whsec_... → STRIPE_WEBHOOK_SECRET, restart API

# Terminal C — fire fixtures
./scripts/stripe_cli_test.sh trigger
./scripts/stripe_cli_test.sh status
```

Handled events:

- `checkout.session.completed`
- `customer.subscription.created` / `updated` / `deleted`
- `invoice.paid` / `invoice.payment_failed`

## Script exit codes (`stripe_cli_test.sh`)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage / unknown command |
| 2 | Missing dependency (stripe, curl, pytest) |
| 3 | API unreachable or non-2xx status |
| 4 | Stripe CLI command failed (`listen` / all triggers) |
| 5 | Unit tests failed |

Hints:

- Auth errors from Stripe CLI → `stripe login`
- `status` connection refused → start the API; check `BASE_URL`
- Partial trigger failures → non-fatal unless `STRICT_TRIGGER=1`

## Without Stripe CLI (signed local POST)

```bash
# Unit tests (no network / DB)
./scripts/stripe_cli_test.sh unit
# or: pytest tests/test_stripe_webhook.py -q

# Sign + POST a fixture
python scripts/stripe_sign_payload.py \
  --secret "$STRIPE_WEBHOOK_SECRET" \
  --event invoice.paid \
  --tenant-id <uuid> \
  --organization-id <uuid> \
  --plan-code professional \
  --post
```

`stripe_sign_payload.py` exit codes: `0` ok · `1` HTTP/usage · `2` file/JSON · `3` network.

## Link events to a tenant

Put metadata on Checkout / Subscription objects (or inject via `stripe_sign_payload.py`):

| Key | Purpose |
|-----|---------|
| `tenant_id` | Resolve / create `TenantSubscription` |
| `organization_id` | Same, via org |
| `plan_code` | Map to `BillingPlan.code` |

Alternatively set `external_customer_id` / `external_subscription_id` on an existing subscription row so invoice/subscription events match.

## Verify

```http
GET /api/v1/msp/billing/stripe/status
GET /api/v1/msp/tenants/{tenant_id}/subscription
```

DB: `stripe_webhook_events` (idempotent log), `tenant_subscriptions.status` / periods.
