#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
  if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="$VIRTUAL_ENV/Scripts/python.exe"
  fi
elif [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="$REPO_ROOT/.venv/Scripts/python.exe"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python was not found in PATH" >&2
  exit 1
fi

echo "== health =="
curl -sS "$BASE/health" | head -c 400; echo

echo "== runtime enroll =="
ENROLL=$(curl -sS -X POST "$BASE/api/v1/runtime/enroll" \
  -H 'Content-Type: application/json' \
  -d '{"hostname":"smoke-host","agent_version":"1.0.0"}')
echo "$ENROLL"
AGENT_ID=$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['agent_id'])" <<<"$ENROLL")
TOKEN=$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['agent_token'])" <<<"$ENROLL")

echo "== heartbeat =="
curl -sS -X POST "$BASE/api/v1/runtime/heartbeat" \
  -H 'Content-Type: application/json' \
  -d "{\"agent_id\":\"$AGENT_ID\",\"agent_token\":\"$TOKEN\",\"status\":\"online\",\"cpu_percent\":12.5}"
echo

echo "== queue command =="
CMD=$(curl -sS -X POST "$BASE/api/v1/runtime/agents/$AGENT_ID/commands" \
  -H 'Content-Type: application/json' \
  -d '{"command":"echo hello-bhudi"}')
echo "$CMD"
CMD_ID=$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['command_id'])" <<<"$CMD")

echo "== pending =="
curl -sS "$BASE/api/v1/runtime/agents/$AGENT_ID/commands/pending?agent_token=$TOKEN"
echo

echo "== result =="
curl -sS -X POST "$BASE/api/v1/runtime/agents/$AGENT_ID/commands/$CMD_ID/result?agent_token=$TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"exit_code":0,"stdout":"hello-bhudi\n","stderr":""}'
echo

echo "== devices status =="
curl -sS "$BASE/api/v1/devices/status"
echo
echo "SMOKE OK"
