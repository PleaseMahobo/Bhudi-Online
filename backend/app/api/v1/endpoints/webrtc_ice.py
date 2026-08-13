"""Public ICE server config for WebRTC remote desktop clients."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/webrtc", tags=["webrtc"])


def _split_urls(raw: str) -> list[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


@router.get("/ice-servers")
def get_ice_servers() -> dict[str, Any]:
    """Return ICE servers for browser + agent WebRTC peers.

    Configure via env:
      WEBRTC_STUN_URLS=stun:stun.l.google.com:19302,stun:turn.example:3478
      WEBRTC_TURN_URLS=turn:turn.example:3478
      WEBRTC_TURN_USERNAME=...
      WEBRTC_TURN_PASSWORD=...
    """
    stun_urls = _split_urls(
        os.getenv("WEBRTC_STUN_URLS", "stun:stun.l.google.com:19302")
    )
    turn_urls = _split_urls(os.getenv("WEBRTC_TURN_URLS", ""))
    turn_user = os.getenv("WEBRTC_TURN_USERNAME", "")
    turn_pass = os.getenv("WEBRTC_TURN_PASSWORD", "")

    servers: list[dict[str, Any]] = []
    if stun_urls:
        servers.append({"urls": stun_urls})
    if turn_urls and turn_user and turn_pass:
        servers.append(
            {
                "urls": turn_urls,
                "username": turn_user,
                "credential": turn_pass,
            }
        )

    return {"iceServers": servers}
