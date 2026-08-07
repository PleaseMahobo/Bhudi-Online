#!/usr/bin/env sh
# Stripe CLI local webhook testing for Bhudi Online MSP billing.
#
# Prerequisites:
#   1. Stripe CLI installed: https://stripe.com/docs/stripe-cli
#   2. Logged in: stripe login
#   3. API running locally (default http://127.0.0.1:8000)
#   4. Migration applied: alembic upgrade head
#
# Usage:
#   ./scripts/stripe_cli_test.sh              # print instructions + status check
#   ./scripts/stripe_cli_test.sh listen       # stripe listen → forward webhooks
#   ./scripts/stripe_cli_test.sh trigger      # fire sample events (listen must be running)
#   ./scripts/stripe_cli_test.sh status       # GET /msp/billing/stripe/status
#   ./scripts/stripe_cli_test.sh unit         # run pytest signature tests
#
# Workflow:
#   Terminal A:  STRIPE_ENABLED=true STRIPE_WEBHOOK_SECRET=whsec_... uvicorn ...
#   Terminal B:  ./scripts/stripe_cli_test.sh listen
#                → copy the printed whsec_... into .env as STRIPE_WEBHOOK_SECRET
#   Terminal C:  ./scripts/stripe_cli_test.sh trigger

set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
WEBHOOK_PATH="${WEBHOOK_PATH:-/api/v1/msp/billing/stripe/webhook}"
FORWARD_TO="${FORWARD_TO:-${BASE_URL}${WEBHOOK_PATH}}"

cmd="${1:-help}"

need_stripe() {
  if ! command -v stripe >/dev/null 2>&1; then
    echo "Stripe CLI not found. Install: https://stripe.com/docs/stripe-cli" >&2
    exit 1
  fi
}

print_help() {
  cat <<EOF
Stripe CLI testing — Bhudi Online

  status   GET ${BASE_URL}/api/v1/msp/billing/stripe/status
  listen   stripe listen --forward-to ${FORWARD_TO}
  trigger  Fire handled event types via stripe trigger
  unit     pytest tests/test_stripe_webhook.py
  help     This message

Env:
  BASE_URL       API base (default ${BASE_URL})
  WEBHOOK_PATH   Path (default ${WEBHOOK_PATH})
  FORWARD_TO     Override full forward URL

Typical session:
  1. export STRIPE_ENABLED=true
  2. ./scripts/stripe_cli_test.sh listen
     → set STRIPE_WEBHOOK_SECRET to the printed whsec_... value and restart API
  3. ./scripts/stripe_cli_test.sh trigger
  4. Check API logs / stripe_webhook_events table / subscription rows
EOF
}

do_status() {
  echo "GET ${BASE_URL}/api/v1/msp/billing/stripe/status"
  if command -v curl >/dev/null 2>&1; then
    curl -sS "${BASE_URL}/api/v1/msp/billing/stripe/status" | (command -v python3 >/dev/null 2>&1 && python3 -m json.tool || cat)
    echo
  else
    echo "curl not available" >&2
    exit 1
  fi
}

do_listen() {
  need_stripe
  echo "Forwarding Stripe events → ${FORWARD_TO}"
  echo "Copy the webhook signing secret (whsec_...) into STRIPE_WEBHOOK_SECRET and ensure STRIPE_ENABLED=true."
  echo
  exec stripe listen \
    --forward-to "${FORWARD_TO}" \
    --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed
}

do_trigger() {
  need_stripe
  echo "Triggering sample events (requires an active 'stripe listen' session)..."
  for ev in \
    checkout.session.completed \
    customer.subscription.created \
    customer.subscription.updated \
    customer.subscription.deleted \
    invoice.paid \
    invoice.payment_failed
  do
    echo "--- stripe trigger ${ev}"
    stripe trigger "${ev}" || echo "(trigger ${ev} failed — fixture may be unavailable in this CLI version)"
  done
  echo "Done. Inspect API logs and GET ${BASE_URL}/api/v1/msp/billing/stripe/status"
}

do_unit() {
  cd "${ROOT}"
  if command -v pytest >/dev/null 2>&1; then
    pytest tests/test_stripe_webhook.py -q
  else
    python3 -m pytest tests/test_stripe_webhook.py -q
  fi
}

case "${cmd}" in
  help|-h|--help) print_help ;;
  status) do_status ;;
  listen) do_listen ;;
  trigger) do_trigger ;;
  unit) do_unit ;;
  *)
    echo "Unknown command: ${cmd}" >&2
    print_help
    exit 1
    ;;
esac
