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
#   ./scripts/stripe_cli_test.sh              # help
#   ./scripts/stripe_cli_test.sh listen       # stripe listen → forward webhooks
#   ./scripts/stripe_cli_test.sh trigger      # fire sample events (listen must be running)
#   ./scripts/stripe_cli_test.sh status       # GET /msp/billing/stripe/status
#   ./scripts/stripe_cli_test.sh unit         # run pytest signature tests
#
# Exit codes:
#   0  success
#   1  usage / validation error
#   2  missing dependency (stripe CLI, curl, pytest)
#   3  API unreachable or HTTP error
#   4  Stripe CLI command failed
#   5  unit tests failed

set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
WEBHOOK_PATH="${WEBHOOK_PATH:-/api/v1/msp/billing/stripe/webhook}"
FORWARD_TO="${FORWARD_TO:-${BASE_URL}${WEBHOOK_PATH}}"
# If set to 1, trigger exits non-zero when any event fails (default: only when all fail)
STRICT_TRIGGER="${STRICT_TRIGGER:-0}"
CURL_CONNECT_TIMEOUT="${CURL_CONNECT_TIMEOUT:-3}"
CURL_MAX_TIME="${CURL_MAX_TIME:-15}"

cmd="${1:-help}"

die() {
  code="$1"
  shift
  echo "error: $*" >&2
  exit "$code"
}

info() { echo "$*"; }
warn() { echo "warning: $*" >&2; }

need_cmd() {
  name="$1"
  hint="${2:-}"
  if ! command -v "$name" >/dev/null 2>&1; then
    if [ -n "$hint" ]; then
      die 2 "'$name' not found. $hint"
    fi
    die 2 "'$name' not found on PATH"
  fi
}

need_stripe() {
  need_cmd stripe "Install: https://stripe.com/docs/stripe-cli"
  # Best-effort auth check (non-fatal if offline / older CLI)
  if ! stripe config --list >/dev/null 2>&1; then
    warn "stripe config unreadable — run 'stripe login' if listen/trigger fail"
  fi
}

need_curl() {
  need_cmd curl "Install curl to probe the API"
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
  BASE_URL              API base (default ${BASE_URL})
  WEBHOOK_PATH          Path (default ${WEBHOOK_PATH})
  FORWARD_TO            Override full forward URL
  STRICT_TRIGGER=1      Exit non-zero if any trigger fails
  CURL_CONNECT_TIMEOUT  Seconds (default ${CURL_CONNECT_TIMEOUT})
  CURL_MAX_TIME         Seconds (default ${CURL_MAX_TIME})

Exit codes: 0 ok · 1 usage · 2 missing dep · 3 API error · 4 stripe CLI · 5 tests

Typical session:
  1. export STRIPE_ENABLED=true
  2. ./scripts/stripe_cli_test.sh listen
     → set STRIPE_WEBHOOK_SECRET to the printed whsec_... value and restart API
  3. ./scripts/stripe_cli_test.sh trigger
  4. ./scripts/stripe_cli_test.sh status
EOF
}

do_status() {
  need_curl
  url="${BASE_URL}/api/v1/msp/billing/stripe/status"
  info "GET ${url}"

  tmp="$(mktemp 2>/dev/null || echo "/tmp/stripe_cli_status_$$")"
  # shellcheck disable=SC2064
  trap 'rm -f "$tmp"' EXIT

  set +e
  http_code="$(curl -sS \
    --connect-timeout "${CURL_CONNECT_TIMEOUT}" \
    --max-time "${CURL_MAX_TIME}" \
    -o "$tmp" \
    -w "%{http_code}" \
    "$url" 2>"${tmp}.err")"
  curl_rc=$?
  set -e

  if [ "$curl_rc" -ne 0 ]; then
    err_msg="$(cat "${tmp}.err" 2>/dev/null || true)"
    rm -f "${tmp}.err"
    die 3 "API unreachable at ${url} (curl exit ${curl_rc}). Is the server running? ${err_msg}"
  fi
  rm -f "${tmp}.err"

  case "$http_code" in
    200|201)
      if command -v python3 >/dev/null 2>&1; then
        python3 -m json.tool <"$tmp" || cat "$tmp"
      else
        cat "$tmp"
      fi
      echo
      ;;
    000)
      die 3 "No HTTP response from ${url}. Check BASE_URL and that the API is listening."
      ;;
    *)
      body="$(cat "$tmp" 2>/dev/null || true)"
      die 3 "HTTP ${http_code} from ${url}${body:+ — ${body}}"
      ;;
  esac
}

do_listen() {
  need_stripe
  info "Forwarding Stripe events → ${FORWARD_TO}"
  info "Copy the webhook signing secret (whsec_...) into STRIPE_WEBHOOK_SECRET and ensure STRIPE_ENABLED=true."
  info "If listen fails with auth errors, run: stripe login"
  echo

  set +e
  stripe listen \
    --forward-to "${FORWARD_TO}" \
    --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed
  rc=$?
  set -e

  if [ "$rc" -ne 0 ]; then
    die 4 "stripe listen exited with code ${rc}. Check login (stripe login), network, and FORWARD_TO=${FORWARD_TO}"
  fi
}

do_trigger() {
  need_stripe
  info "Triggering sample events (requires an active 'stripe listen' session)..."

  ok=0
  fail=0
  failed_events=""

  for ev in \
    checkout.session.completed \
    customer.subscription.created \
    customer.subscription.updated \
    customer.subscription.deleted \
    invoice.paid \
    invoice.payment_failed
  do
    info "--- stripe trigger ${ev}"
    set +e
    out="$(stripe trigger "${ev}" 2>&1)"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
      echo "$out"
      ok=$((ok + 1))
    else
      warn "trigger ${ev} failed (exit ${rc})"
      echo "$out" >&2
      fail=$((fail + 1))
      failed_events="${failed_events} ${ev}"
      case "$out" in
        *login*|*authenticated*|*API key*)
          warn "Auth issue detected — run: stripe login"
          ;;
        *not found*|*unknown*|*unsupported*)
          warn "Fixture may be unavailable in this Stripe CLI version"
          ;;
      esac
    fi
  done

  info "Done: ${ok} succeeded, ${fail} failed."
  info "Inspect API logs and: ./scripts/stripe_cli_test.sh status"

  if [ "$fail" -gt 0 ] && [ "$ok" -eq 0 ]; then
    die 4 "All stripe trigger commands failed.${failed_events}"
  fi
  if [ "$fail" -gt 0 ] && [ "$STRICT_TRIGGER" = "1" ]; then
    die 4 "Some triggers failed (STRICT_TRIGGER=1):${failed_events}"
  fi
  if [ "$fail" -gt 0 ]; then
    warn "Partial success — failed events:${failed_events}"
  fi
}

do_unit() {
  cd "${ROOT}" || die 1 "Cannot cd to backend root: ${ROOT}"

  set +e
  if command -v pytest >/dev/null 2>&1; then
    pytest tests/test_stripe_webhook.py -q
    rc=$?
  elif python3 -m pytest --version >/dev/null 2>&1; then
    python3 -m pytest tests/test_stripe_webhook.py -q
    rc=$?
  else
    set -e
    die 2 "pytest not found. Install with: pip install pytest"
  fi
  set -e

  if [ "$rc" -ne 0 ]; then
    die 5 "Unit tests failed (exit ${rc})"
  fi
  info "Unit tests passed"
}

case "${cmd}" in
  help|-h|--help) print_help ;;
  status) do_status ;;
  listen) do_listen ;;
  trigger) do_trigger ;;
  unit) do_unit ;;
  *)
    echo "error: unknown command: ${cmd}" >&2
    print_help
    exit 1
    ;;
esac
