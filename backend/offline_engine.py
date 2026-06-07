# offline_engine.py

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from supabase import create_client

# -----------------------------
# CONFIG
# -----------------------------
SUPABASE_URL = "https://fwlaecnopjckrdvwlbpw.supabase.co"
SUPABASE_KEY = "sb_publishable_xVX17Q1qwYqnUGfuP_dEuQ_Pl4TN7zs"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CHECK_INTERVAL = 10  # seconds

OFFLINE_THRESHOLD = 90      # seconds
DEGRADED_THRESHOLD = 45     # seconds

MAX_MISSES_OFFLINE = 5
MAX_MISSES_DEGRADED = 3

# -----------------------------
# OPTIONAL HOOKS (plug in later)
# -----------------------------
async def send_alert(device: Dict[str, Any], status: str):
    """
    Webhook / email / Slack integration point
    """
    print(f"[ALERT] Device {device['id']} changed to {status}")


async def push_websocket_update(device_id: str, status: str, score: int):
    """
    Placeholder for WebSocket broadcast to frontend dashboard
    """
    print(f"[WS] {device_id} -> {status} ({score})")


# -----------------------------
# CORE LOGIC
# -----------------------------
def calculate_health_score(missed: int, delta_seconds: float) -> int:
    """
    Simple health scoring model
    """
    score = 100

    score -= missed * 10
    score -= int(delta_seconds // 10)

    return max(0, min(score, 100))


def determine_status(delta: float, missed: int) -> str:
    """
    Multi-layer decision engine
    """

    if missed >= MAX_MISSES_OFFLINE or delta > OFFLINE_THRESHOLD:
        return "offline"

    if missed >= MAX_MISSES_DEGRADED or delta > DEGRADED_THRESHOLD:
        return "degraded"

    return "online"


# -----------------------------
# MAIN ENGINE LOOP
# -----------------------------
async def offline_detection_engine():
    """
    Continuously monitors device heartbeat status
    """

    print("[ENGINE] Offline Detection Engine started...")

    while True:
        try:
            now = datetime.now(timezone.utc)

            response = supabase.table("devices").select("*").execute()
            devices: List[Dict[str, Any]] = response.data or []

            for device in devices:
                last_seen = device.get("last_seen")
                missed = device.get("missed_heartbeats", 0)

                if not last_seen:
                    continue

                last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))

                delta = (now - last_seen_dt).total_seconds()

                new_status = determine_status(delta, missed)
                health_score = calculate_health_score(missed, delta)

                current_status = device.get("status")

                # -----------------------------
                # STATUS CHANGE DETECTION
                # -----------------------------
                if new_status != current_status:

                    # update DB
                    supabase.table("devices").update({
                        "status": new_status,
                        "health_score": health_score,
                        "missed_heartbeats": missed + 1 if new_status != "online" else 0
                    }).eq("id", device["id"]).execute()

                    # alert hook
                    await send_alert(device, new_status)

                    # websocket push
                    await push_websocket_update(
                        device_id=device["id"],
                        status=new_status,
                        score=health_score
                    )

                else:
                    # periodic health refresh
                    supabase.table("devices").update({
                        "health_score": health_score
                    }).eq("id", device["id"]).execute()

        except Exception as e:
            print(f"[ENGINE ERROR] {e}")

        await asyncio.sleep(CHECK_INTERVAL)


# -----------------------------
# HEARTBEAT HANDLER (API SIDE)
# -----------------------------
async def register_heartbeat(device_id: str):
    """
    Called by /api/heartbeat endpoint
    """

    now = datetime.now(timezone.utc).isoformat()

    supabase.table("devices").update({
        "last_seen": now,
        "status": "online",
        "missed_heartbeats": 0
    }).eq("id", device_id).execute()


# -----------------------------
# STARTUP HOOK (FASTAPI)
# -----------------------------
def start_engine(app):
    """
    Attach this in main.py
    """

    @app.on_event("startup")
    async def _start():
        asyncio.create_task(offline_detection_engine())