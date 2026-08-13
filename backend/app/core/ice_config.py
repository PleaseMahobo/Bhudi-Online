"""Shared WebRTC ICE server configuration from environment."""
from __future__ import annotations

import os
from typing import Any


def _split_urls(raw: str) -> list[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def get_ice_servers() -> list[dict[str, Any]]:
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
    return servers
