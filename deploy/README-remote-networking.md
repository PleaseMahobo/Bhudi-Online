# Bhudi remote access networking (nginx + STUN/TURN)

## Architecture

```
Browser  --WSS-->  nginx (api.bhudi.online)  --WS-->  FastAPI (Railway/Docker)
Agent    --WSS-->  nginx / Railway API
Browser  <--WebRTC media-->  Agent
              \                /
               \-- via TURN --/   (only if P2P ICE fails)
```

- **Signaling** (session control, offers, ICE candidates): WebSocket through nginx → FastAPI.
- **Media** (screen frames via WebRTC): UDP between agent and browser; **TURN** relays when NAT blocks P2P.

## 1. nginx WebSocket proxy

File: `deploy/nginx/bhudi-api-websocket.conf`

1. Point `upstream bhudi_api` at your FastAPI listen address.
2. Set `server_name` + TLS certs for `api.bhudi.online`.
3. Enable site and reload:

```bash
sudo ln -sf /path/to/bhudi-api-websocket.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Critical directives for WebSockets:

- `proxy_http_version 1.1`
- `Upgrade` + `Connection` headers via `$connection_upgrade` map
- Long `proxy_read_timeout` / `proxy_send_timeout` (desktop sessions)
- `proxy_buffering off`

Frontend / agent should use:

```text
NEXT_PUBLIC_API_URL=https://api.bhudi.online
# WebSocket becomes wss://api.bhudi.online/...
```

If you stay on `*.up.railway.app`, Railway already terminates TLS; nginx is optional unless you want a custom domain in front of the API.

## 2. STUN / TURN (coturn)

Files:

- `deploy/coturn/turnserver.conf`
- `deploy/coturn/docker-compose.turn.yml`

### Quick start (VM)

```bash
sudo apt update && sudo apt install -y coturn
sudo sed -i 's/#TURNSERVER_ENABLED=1/TURNSERVER_ENABLED=1/' /etc/default/coturn
# Edit external-ip, user, realm in turnserver.conf then:
sudo cp deploy/coturn/turnserver.conf /etc/turnserver.conf
sudo systemctl enable --now coturn
sudo systemctl status coturn
```

Open firewall:

- `3478/tcp`, `3478/udp`
- `49160-49200/udp` (relay range in sample config)

### Env for API + agent

```text
# Railway backend / agent environment
WEBRTC_STUN_URLS=stun:stun.l.google.com:19302,stun:turn.bhudi.online:3478
WEBRTC_TURN_URLS=turn:turn.bhudi.online:3478
WEBRTC_TURN_USERNAME=bhudi
WEBRTC_TURN_PASSWORD=CHANGE_ME_STRONG_PASSWORD
```

Public Google STUN is fine for discovery; **TURN must be your own server** for reliable remote desktop across strict NATs.

## 3. Verify

```bash
# STUN binding (optional tool)
# turnutils_stunclient turn.bhudi.online

# TURN credentials
turnutils_uclient -v -u bhudi -w 'CHANGE_ME_STRONG_PASSWORD' turn.bhudi.online
```

Browser DevTools → Network → WS should show `wss://api.bhudi.online/api/v1/remote-access/sessions/.../dashboard` **101 Switching Protocols**.

## 4. Railway-only (no custom nginx)

If the API stays on Railway without nginx:

1. Set `NEXT_PUBLIC_API_URL=https://bhudi-online-production.up.railway.app`
2. Still run **coturn** on a small VPS for TURN
3. Pass `WEBRTC_TURN_*` into the agent and backend ICE config endpoint
