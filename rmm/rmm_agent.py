import time
import socket
import platform
import requests
from datetime import datetime

# =========================
# CONFIG
# =========================
SERVER_URL = "http://127.0.0.1:8000"
HEARTBEAT_INTERVAL = 10  # seconds

# =========================
# DEVICE INFO
# =========================
def get_device_id():
    return socket.gethostname()

def get_hostname():
    return platform.node()

# =========================
# REGISTER DEVICE (optional but recommended)
# =========================
def register_device():
    payload = {
        "device_id": get_device_id(),
        "hostname": get_hostname(),
        "ip_address": None
    }

    try:
        r = requests.post(f"{SERVER_URL}/api/devices/register", json=payload, timeout=5)
        print("[REGISTER]", r.status_code, r.text)
    except Exception as e:
        print("[REGISTER ERROR]", e)

# =========================
# HEARTBEAT
# =========================
def send_heartbeat():
    payload = {
        "device_id": get_device_id(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "online"
    }

    try:
        r = requests.post(f"{SERVER_URL}/api/heartbeat", json=payload, timeout=5)

        if r.status_code == 200:
            print("[HEARTBEAT] OK")
        else:
            print("[HEARTBEAT] FAIL", r.status_code, r.text)

    except Exception as e:
        print("[HEARTBEAT ERROR]", e)

# =========================
# MAIN LOOP
# =========================
def run():
    print("RMM Agent starting...")
    print("Device:", get_device_id())

    register_device()

    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL)

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    run()