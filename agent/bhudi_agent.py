"""
Bhudi RMM — unified production agent (Phase B + Phase 11 Software Deployment + Sprint 3 Real Command Framework)

Loop:
  1. Enroll (or load saved identity)
  2. Heartbeat + metrics
  3. Poll pending commands
  4. Poll pending software deployments
  5. Execute and post results
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
    from .command_framework import execute_named
    from .executor import execute_command_record
    from .streaming_session import streaming_session_coordinator
    from .software_deploy import execute_deployment
except ImportError:
    from command_framework import execute_named
    from executor import execute_command_record
    from streaming_session import streaming_session_coordinator
    from software_deploy import execute_deployment

try:
    import psutil
except ImportError:
    psutil = None

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

DEFAULT_CONFIG_PATH = Path(__file__).with_name("agent_config.json")
DEFAULT_IDENTITY_PATH = Path(__file__).with_name("agent_identity.json")
CONFIG_PATH = Path(os.getenv("BHUDI_CONFIG_PATH") or DEFAULT_CONFIG_PATH)
IDENTITY_PATH = Path(os.getenv("BHUDI_IDENTITY_PATH") or DEFAULT_IDENTITY_PATH)


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def server_url() -> str:
    cfg = load_json(CONFIG_PATH)
    url = os.getenv("BHUDI_SERVER_URL") or cfg.get("server_url") or "http://127.0.0.1:8000"
    return url.rstrip("/")


def api(path: str) -> str:
    return f"{server_url()}/api/v1{path}"


def agent_hostname() -> str:
    return os.getenv("BHUDI_HOSTNAME") or socket.gethostname()


def metrics() -> dict:
    out = {"cpu_percent": None, "memory_percent": None, "disk_percent": None, "ip_address": None, "hostname": agent_hostname()}
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
    body = {"hostname": agent_hostname(), "agent_version": "1.2.0-sprint-3", "platform": platform.platform(), "enrollment_secret": os.getenv("BHUDI_ENROLL_SECRET") or "phase-ab-test"}
    r = requests.post(api("/runtime/enroll"), json=body, timeout=15)
    r.raise_for_status()
    data = r.json()
    save_json(IDENTITY_PATH, data)
    print(f"[enroll] agent_id={data['agent_id']}")
    return data


def load_identity() -> dict:
    if os.getenv("BHUDI_AGENT_ID") and os.getenv("BHUDI_AGENT_TOKEN"):
        return {"agent_id": os.getenv("BHUDI_AGENT_ID"), "agent_token": os.getenv("BHUDI_AGENT_TOKEN")}
    data = load_json(IDENTITY_PATH)
    if data.get("agent_id") and data.get("agent_token"):
        return data
    return enroll()


def send_heartbeat(ident: dict) -> dict:
    body = {"agent_id": ident["agent_id"], "agent_token": ident["agent_token"], "status": "online", **metrics()}
    r = requests.post(api("/runtime/heartbeat"), json=body, timeout=15)
    if r.status_code == 401:
        print("[heartbeat] unauthorized — re-enrolling")
        ident.update(enroll())
        body["agent_id"], body["agent_token"] = ident["agent_id"], ident["agent_token"]
        r = requests.post(api("/runtime/heartbeat"), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def poll_commands(ident: dict) -> list:
    r = requests.get(api(f"/runtime/agents/{ident['agent_id']}/commands/pending"), params={"agent_token": ident["agent_token"]}, timeout=15)
    r.raise_for_status()
    return r.json().get("commands") or []


def poll_enterprise_commands(ident: dict) -> list:
    r = requests.get(api(f"/agent/{enterprise_agent_id(ident)}/commands"), timeout=15)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()


def mark_enterprise_command_sent(ident: dict, command_id: str) -> None:
    r = requests.post(api(f"/agent/{enterprise_agent_id(ident)}/commands/{command_id}/sent"), timeout=15)
    r.raise_for_status()


def post_enterprise_result(ident: dict, command_id: str, result: dict) -> None:
    agent_id = enterprise_agent_id(ident)
    endpoint = "completed" if int(result.get("exit_code", 1)) == 0 else "failed"
    payload = result if endpoint == "completed" else {"message": result.get("stderr") or result.get("stdout") or "remote command failed"}
    r = requests.post(api(f"/agent/{agent_id}/commands/{command_id}/{endpoint}"), json=payload, timeout=15)
    r.raise_for_status()


def enterprise_agent_id(ident: dict) -> str:
    return str(os.getenv("BHUDI_ENTERPRISE_AGENT_ID") or ident["agent_id"])


def is_interactive_remote_session(command: dict) -> bool:
    command_type = str(command.get("command_type") or "")
    payload = command.get("payload") or {}
    return command_type == "remote.desktop.start" or (command_type == "remote.terminal.start" and payload.get("interactive", True))


def execute(command: str, shell: bool = True) -> dict:
    try:
        completed = subprocess.run(command, shell=shell, capture_output=True, text=True, timeout=120)
        return {"exit_code": completed.returncode, "stdout": (completed.stdout or "")[:50_000], "stderr": (completed.stderr or "")[:20_000]}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "command timed out"}
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


def post_result(ident: dict, command_id: str, result: dict) -> None:
    r = requests.post(api(f"/runtime/agents/{ident['agent_id']}/commands/{command_id}/result"), params={"agent_token": ident["agent_token"]}, json=result, timeout=15)
    r.raise_for_status()


def poll_deployments(ident: dict) -> list:
    params: dict = {"hostname": agent_hostname()}
    device_id = os.getenv("BHUDI_DEVICE_ID")
    if device_id: params["device_id"] = device_id
    if ident.get("agent_id"): params["agent_id"] = ident["agent_id"]
    try:
        r = requests.get(api("/software-deployment/agent/pending"), params=params, timeout=15)
        if r.status_code == 404: return []
        r.raise_for_status()
        return r.json().get("deployments") or []
    except Exception as e:
        print(f"[deploy] poll error: {e}")
        return []


def report_deployment(job_id: str, target_id: str, result: dict) -> None:
    body = {"status": result.get("status", "failed"), "exit_code": result.get("exit_code"), "stdout": result.get("stdout"), "stderr": result.get("stderr"), "error_message": result.get("error_message"), "download_bytes": result.get("download_bytes"), "duration_ms": result.get("duration_ms"), "reboot_required": bool(result.get("reboot_required"))}
    r = requests.post(api(f"/software-deployment/jobs/{job_id}/targets/{target_id}/report"), json=body, timeout=30)
    r.raise_for_status()


def process_deployments(ident: dict) -> None:
    deployments = poll_deployments(ident)
    for dep in deployments:
        job_id, target_id = str(dep.get("job_id") or ""), str(dep.get("target_id") or "")
        def _progress(partial: dict) -> None:
            try: report_deployment(job_id, target_id, partial)
            except Exception as e: print(f"[deploy] progress report failed: {e}")
        result = execute_deployment(dep, report=_progress)
        try: report_deployment(job_id, target_id, result)
        except Exception as e: print(f"[deploy] final report failed: {e}")


def execute_enterprise_command(command: dict) -> dict:
    command_type = str(command.get("command_type") or "")
    payload = command.get("payload") or {}
    if command_type in {"inventory", "processes", "services", "software", "windows_updates", "event_logs", "network", "disks", "printers", "remote_script", "remote_powershell"}:
        return execute_named(command_type, payload)
    if is_interactive_remote_session(command):
        return streaming_session_coordinator.start(server_url=server_url(), agent_id=enterprise_agent_id(_CURRENT_IDENTITY), command=command)
    return execute_command_record(command)

_CURRENT_IDENTITY: dict = {}


def run_once(ident: dict) -> None:
    global _CURRENT_IDENTITY
    _CURRENT_IDENTITY = ident
    hb = send_heartbeat(ident)
    print(f"[heartbeat] ok pending={hb.get('pending_commands', 0)}")

    for command in poll_enterprise_commands(ident):
        command_id = command.get("command_id") or command.get("id")
        if not command_id: continue
        print(f"[enterprise-command] {command_id}: {command.get('command_type')}")
        mark_enterprise_command_sent(ident, str(command_id))
        result = execute_enterprise_command(command)
        post_enterprise_result(ident, str(command_id), result)
        print(f"[enterprise-result] exit={result.get('exit_code')}")

    for cmd in poll_commands(ident):
        print(f"[command] {cmd['command_id']}: {cmd['command']}")
        result = execute(cmd["command"], shell=cmd.get("shell", True))
        post_result(ident, cmd["command_id"], result)
        print(f"[result] exit={result['exit_code']}")

    process_deployments(ident)


def main() -> None:
    print(f"[bhudi-agent] server={server_url()}")
    ident = load_identity()
    print(f"[bhudi-agent] agent_id={ident['agent_id']} host={agent_hostname()}")
    interval = int(os.getenv("BHUDI_HEARTBEAT_INTERVAL", "10"))
    run_once(ident)
    if os.getenv("BHUDI_RUN_ONCE", "0").lower() in {"1", "true", "yes"}:
        return
    while True:
        try: run_once(ident)
        except Exception as e: print(f"[error] {e}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
