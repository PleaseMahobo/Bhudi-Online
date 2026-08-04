"""
Bhudi RMM — unified production agent (Phase B)

Loop:
  1. Enroll (or load saved identity)
  2. Heartbeat + metrics
  3. Poll pending commands
  4. Execute and post results

Config (env overrides agent_config.json):
  BHUDI_SERVER_URL   e.g. http://127.0.0.1:8000
  BHUDI_AGENT_ID
  BHUDI_AGENT_TOKEN
  BHUDI_HOSTNAME
"""
from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

CONFIG_PATH = Path(__file__).with_name("agent_config.json")
IDENTITY_PATH = Path(__file__).with_name("agent_identity.json")


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def server_url() -> str:
    cfg = load_json(CONFIG_PATH)
    url = os.getenv("BHUDI_SERVER_URL") or cfg.get("server_url") or "http://127.0.0.1:8000"
    return url.rstrip("/")


def api(path: str) -> str:
    return f"{server_url()}/api/v1{path}"


def metrics() -> dict:
    out = {
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "ip_address": None,
        "hostname": socket.gethostname(),
    }
    try:
        out["ip_address"] = socket.gethostbyname(socket.gethostname())
    except Exception:
        pass
    if psutil:
        try:
            out["cpu_percent"] = psutil.cpu_percent(interval=0.3)
            out["memory_percent"] = psutil.virtual_memory().percent
            out["disk_percent"] = psutil.disk_usage("/" if os.name != "nt" else "C:\\").percent
        except Exception:
            pass
    return out


def enroll() -> dict:
    body = {
        "hostname": os.getenv("BHUDI_HOSTNAME") or socket.gethostname(),
        "agent_version": "1.0.0-phase-b",
        "platform": platform.platform(),
        "enrollment_secret": os.getenv("BHUDI_ENROLL_SECRET") or "phase-ab-test",
    }
    r = requests.post(api("/runtime/enroll"), json=body, timeout=15)
    r.raise_for_status()
    data = r.json()
    save_json(IDENTITY_PATH, data)
    print(f"[enroll] agent_id={data['agent_id']}")
    return data


def load_identity() -> dict:
    if os.getenv("BHUDI_AGENT_ID") and os.getenv("BHUDI_AGENT_TOKEN"):
        return {
            "agent_id": os.getenv("BHUDI_AGENT_ID"),
            "agent_token": os.getenv("BHUDI_AGENT_TOKEN"),
        }
    data = load_json(IDENTITY_PATH)
    if data.get("agent_id") and data.get("agent_token"):
        return data
    return enroll()


def send_heartbeat(ident: dict) -> dict:
    m = metrics()
    body = {
        "agent_id": ident["agent_id"],
        "agent_token": ident["agent_token"],
        "status": "online",
        **m,
    }
    r = requests.post(api("/runtime/heartbeat"), json=body, timeout=15)
    if r.status_code == 401:
        print("[heartbeat] unauthorized — re-enrolling")
        ident.update(enroll())
        body["agent_id"] = ident["agent_id"]
        body["agent_token"] = ident["agent_token"]
        r = requests.post(api("/runtime/heartbeat"), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def poll_commands(ident: dict) -> list:
    r = requests.get(
        api(f"/runtime/agents/{ident['agent_id']}/commands/pending"),
        params={"agent_token": ident["agent_token"]},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("commands") or []


def execute(command: str, shell: bool = True) -> dict:
    try:
        completed = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "exit_code": completed.returncode,
            "stdout": (completed.stdout or "")[:50_000],
            "stderr": (completed.stderr or "")[:20_000],
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "command timed out"}
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


def post_result(ident: dict, command_id: str, result: dict) -> None:
    r = requests.post(
        api(f"/runtime/agents/{ident['agent_id']}/commands/{command_id}/result"),
        params={"agent_token": ident["agent_token"]},
        json=result,
        timeout=15,
    )
    r.raise_for_status()


def run_once(ident: dict) -> None:
    hb = send_heartbeat(ident)
    print(f"[heartbeat] ok pending={hb.get('pending_commands', 0)}")
    for cmd in poll_commands(ident):
        print(f"[command] {cmd['command_id']}: {cmd['command']}")
        result = execute(cmd["command"], shell=cmd.get("shell", True))
        post_result(ident, cmd["command_id"], result)
        print(f"[result] exit={result['exit_code']}")


def main() -> None:
    print(f"[bhudi-agent] server={server_url()}")
    ident = load_identity()
    print(f"[bhudi-agent] agent_id={ident['agent_id']}")
    interval = int(os.getenv("BHUDI_HEARTBEAT_INTERVAL", "10"))
    while True:
        try:
            run_once(ident)
        except Exception as e:
            print(f"[error] {e}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
