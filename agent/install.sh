#!/usr/bin/env bash
# Bhudi RMM Agent installer for Linux / macOS
set -euo pipefail

SERVER_URL="${BHUDI_SERVER_URL:-https://bhudi-online-production.up.railway.app}"
SERVER_URL="${SERVER_URL%/}"
INSTALL_DIR="${BHUDI_INSTALL_DIR:-$HOME/.local/share/bhudi-agent}"
REPO_ZIP_URL="${BHUDI_REPO_ZIP:-https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip}"
CREATE_SERVICE="${BHUDI_CREATE_SERVICE:-1}"

log()  { printf '\033[36m[Bhudi]\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m[Bhudi]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[Bhudi]\033[0m %s\n' "$*"; }
die()  { printf '\033[31m[Bhudi]\033[0m %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-url) SERVER_URL="${2%/}"; shift 2 ;;
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --no-service) CREATE_SERVICE=0; shift ;;
    -h|--help)
      cat <<EOF
Usage: install.sh [--server-url URL] [--install-dir DIR] [--no-service]
Environment: BHUDI_SERVER_URL, BHUDI_INSTALL_DIR, BHUDI_REPO_ZIP
EOF
      exit 0
      ;;
    *) die "Unknown arg: $1" ;;
  esac
done

command -v python3 >/dev/null || die "python3 is required"
command -v unzip >/dev/null || die "unzip is required"
command -v curl >/dev/null || die "curl is required"

log "Server URL: $SERVER_URL"
log "Install dir: $INSTALL_DIR"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

log "Downloading agent package..."
curl -fsSL "$REPO_ZIP_URL" -o "$TMP/repo.zip"
unzip -q "$TMP/repo.zip" -d "$TMP"
SRC="$(find "$TMP" -type d -name agent | head -1)"
[[ -f "$SRC/main.py" ]] || die "agent/main.py not found in archive"

mkdir -p "$INSTALL_DIR"
cp -a "$SRC"/. "$INSTALL_DIR"/

cat > "$INSTALL_DIR/agent_config.json" <<EOF
{
  "server_url": "$SERVER_URL",
  "heartbeat_interval": 10
}
EOF

log "Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
# shellcheck disable=SC1091
source "$INSTALL_DIR/.venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$INSTALL_DIR/requirements.txt"

RUNNER="$INSTALL_DIR/run-agent.sh"
cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
export BHUDI_SERVER_URL="$SERVER_URL"
cd "$INSTALL_DIR"
exec "$INSTALL_DIR/.venv/bin/python" main.py
EOF
chmod +x "$RUNNER"

if [[ "$CREATE_SERVICE" == "1" ]]; then
  if [[ "$(uname -s)" == "Linux" ]] && command -v systemctl >/dev/null && [[ -d /etc/systemd/user || -d "$HOME/.config/systemd/user" ]]; then
    UNIT_DIR="$HOME/.config/systemd/user"
    mkdir -p "$UNIT_DIR"
    cat > "$UNIT_DIR/bhudi-agent.service" <<EOF
[Unit]
Description=Bhudi RMM Agent
After=network-online.target

[Service]
Type=simple
ExecStart=$RUNNER
Restart=always
RestartSec=5
Environment=BHUDI_SERVER_URL=$SERVER_URL

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload || true
    systemctl --user enable --now bhudi-agent.service || warn "Could not enable user service; start manually: $RUNNER"
    ok "systemd user service bhudi-agent enabled"
  else
    warn "No systemd user unit created. Start with: $RUNNER"
    nohup "$RUNNER" >/dev/null 2>&1 &
  fi
else
  warn "Service skipped. Start with: $RUNNER"
fi

ok "Bhudi Agent installed successfully."
echo "  Directory : $INSTALL_DIR"
echo "  Server    : $SERVER_URL"
echo "  Runner    : $RUNNER"
