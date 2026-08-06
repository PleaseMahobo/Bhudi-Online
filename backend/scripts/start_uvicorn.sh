#!/usr/bin/env sh
# Production / local uvicorn launcher with WebSocket memory tuning.
#
# Override any value via environment variables before running.
#
# Examples:
#   ./scripts/start_uvicorn.sh
#   WS_PER_MESSAGE_DEFLATE=false ./scripts/start_uvicorn.sh
#   WS_MAX_SIZE=524288 WS_MAX_QUEUE=8 ./scripts/start_uvicorn.sh

set -eu

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
APP="${APP:-app.main:app}"

# --- WebSocket memory / protocol knobs ---
# Max inbound message size (bytes). Alert batches are small; 1 MiB is plenty.
WS_MAX_SIZE="${WS_MAX_SIZE:-1048576}"

# Max queued inbound frames per connection (websockets impl only).
# Lower = less RAM if a slow client falls behind.
WS_MAX_QUEUE="${WS_MAX_QUEUE:-16}"

# Keepalive
WS_PING_INTERVAL="${WS_PING_INTERVAL:-20}"
WS_PING_TIMEOUT="${WS_PING_TIMEOUT:-20}"

# permessage-deflate (RFC 7692).
# true  → less bandwidth, ~50–300 KB extra RAM per socket (depends on zlib window)
# false → more bandwidth, lower per-connection memory (prefer at high concurrency)
WS_PER_MESSAGE_DEFLATE="${WS_PER_MESSAGE_DEFLATE:-true}"

# Force websockets implementation so max-queue + deflate flags apply.
WS_IMPL="${WS_IMPL:-websockets}"

RELOAD_FLAG=""
if [ "${RELOAD:-0}" = "1" ]; then
  RELOAD_FLAG="--reload"
fi

exec uvicorn "${APP}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --ws "${WS_IMPL}" \
  --ws-max-size "${WS_MAX_SIZE}" \
  --ws-max-queue "${WS_MAX_QUEUE}" \
  --ws-ping-interval "${WS_PING_INTERVAL}" \
  --ws-ping-timeout "${WS_PING_TIMEOUT}" \
  --ws-per-message-deflate "${WS_PER_MESSAGE_DEFLATE}" \
  ${RELOAD_FLAG}
