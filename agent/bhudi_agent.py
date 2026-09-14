"""
Bhudi RMM — unified production agent.

Loop:
  1. Enroll (or load saved identity)
  2. Heartbeat + metrics (CPU/RAM/disk + temperature + SMART)
  3. Poll pending enterprise commands
  4. Poll pending runtime commands
  5. Poll pending software deployments
  6. Periodic endpoint-security scan + report
  7. Execute and post results
"""
from __future__ import annotations

import json
import os
import platform
import re
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
    from .endpoint_security import scan_endpoint_security, to_ingest_payloads
except ImportError:
    from command_framework import execute_named
    from executor import execute_command_record
    from streaming_session import streaming_session_coordinator
    from software_deploy import execute_deployment
    from endpoint_security import scan_endpoint_security, to_ingest_payloads

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

SECURITY_SCAN_EVERY = max(1, int(os.getenv("BHUDI_SECURITY_SCAN_EVERY", "6")))
# SMART can be slow; collect every N cycles (default ~2 min at 10s interval)
HARDWARE_SENSOR_EVERY = max(1, int(os.getenv("BHUDI_HARDWARE_SENSOR_EVERY", "12")))
_security_cycle = 0
_hardware_cycle = 0
_cached_temp: float | None = None
_cached_smart_status: str | None = None
_cached_smart_details: dict | None = None


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def _collect_temperature() -> float | None:
    """Best-effort CPU/package temperature in Celsius."""
    if not psutil:
        return None
    try:
        temps = psutil.sensors_temperatures(fahrenheit=False)
        if not temps:
            return None
        # Prefer coretemp / k10temp / acpitz / cpu
        preferred = ("coretemp", "k10temp", "cpu", "acpitz", "pch", "zenpower")
        candidates: list[float] = []
        for name in preferred:
            for key, entries in temps.items():
                if name in key.lower():
                    for e in entries:
                        if e.current is not None:
                            candidates.append(float(e.current))
        if not candidates:
            for entries in temps.values():
                for e in entries:
                    if e.current is not None:
                        candidates.append(float(e.current))
        return max(candidates) if candidates else None
    except Exception:
        return None


def _collect_smart() -> tuple[str | None, dict | None]:
    """Best-effort disk SMART health. Returns (status, details)."""
    details: dict = {"disks": []}

    # Linux: smartctl if present
    if os.name != "nt":
        try:
            # List block devices
            lsblk = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            devices = []
            for line in (lsblk.stdout or "").splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "disk":
                    devices.append(f"/dev/{parts[0]}")
            if not devices:
                devices = ["/dev/sda"]

            overall = "ok"
            for dev in devices[:4]:
                r = subprocess.run(
                    ["smartctl", "-H", "-j", dev],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                entry: dict = {"device": dev, "exit_code": r.returncode}
                try:
                    data = json.loads(r.stdout or "{}")
                    passed = (
                        (data.get("smart_status") or {}).get("passed")
                        if isinstance(data.get("smart_status"), dict)
                        else None
                    )
                    if passed is True:
                        entry["status"] = "ok"
                    elif passed is False:
                        entry["status"] = "failing"
                        overall = "failing"
                    else:
                        # Non-JSON fallback parse
                        text_out = (r.stdout or "") + (r.stderr or "")
                        if re.search(r"PASSED", text_out, re.I):
                            entry["status"] = "ok"
                        elif re.search(r"FAILED|FAILING", text_out, re.I):
                            entry["status"] = "failing"
                            overall = "failing"
                        else:
                            entry["status"] = "unknown"
                            if overall == "ok":
                                overall = "unknown"
                except Exception:
                    text_out = (r.stdout or "") + (r.stderr or "")
                    if re.search(r"PASSED", text_out, re.I):
                        entry["status"] = "ok"
                    elif re.search(r"FAILED|FAILING", text_out, re.I):
                        entry["status"] = "failing"
                        overall = "failing"
                    else:
                        entry["status"] = "unavailable"
                details["disks"].append(entry)

            if details["disks"]:
                return overall, details
        except FileNotFoundError:
            pass
        except Exception as exc:
            details["error"] = str(exc)

    # Windows: Get-PhysicalDisk health
    if os.name == "nt":
        try:
            ps = (
                "Get-PhysicalDisk | Select-Object FriendlyName,HealthStatus,OperationalStatus,"
                "MediaType,Size | ConvertTo-Json -Compress"
            )
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                data = json.loads(r.stdout)
                items = data if isinstance(data, list) else [data]
                overall = "ok"
                for item in items:
                    health = str(item.get("HealthStatus") or "").lower()
                    entry = {
                        "device": item.get("FriendlyName"),
                        "health": item.get("HealthStatus"),
                        "operational": item.get("OperationalStatus"),
                        "media": item.get("MediaType"),
                    }
                    if health in {"healthy", "ok"}:
                        entry["status"] = "ok"
                    elif health in {"warning", "caution"}:
                        entry["status"] = "warning"
                        if overall == "ok":
                            overall = "warning"
                    elif health:
                        entry["status"] = "failing"
                        overall = "failing"
                    else:
                        entry["status"] = "unknown"
                    details["disks"].append(entry)
                if details["disks"]:
                    return overall, details
        except Exception as exc:
            details["error"] = str(exc)

    return None, None


def metrics(include_hardware: bool = False) -> dict:
    global _cached_temp, _cached_smart_status, _cached_smart_details

    out = {
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "ip_address": None,
        "hostname": agent_hostname(),
        "temperature_c": _cached_temp,
        "smart_status": _cached_smart_status,
        "smart_details": _cached_smart_details,
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

    if include_hardware:
        temp = _collect_temperature()
        if temp is not None:
            _cached_temp = temp
            out["temperature_c"] = temp
        smart_status, smart_details = _collect_smart()
        if smart_status is not None:
            _cached_smart_status = smart_status
            _cached_smart_details = smart_details
            out["smart_status"] = smart_status
            out["smart_details"] = smart_details

    return out


def enroll() -> dict:
    body = {
        "hostname": agent_hostname(),
        "agent_version": "1.4.0-health-sensors",
        "platform": platform.platform(),
    }
    enrollment_secret = os.getenv("BHUDI_ENROLL_SECRET")
    if enrollment_secret:
        body["enrollment_secret"] = enrollment_secret
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


def send_heartbeat(ident: dict, include_hardware: bool = False) -> dict:
    body = {
        "agent_id": ident["agent_id"],
        "agent_token": ident["agent_token"],
        "status": "online",
        **metrics(include_hardware=include_hardware),
    }
    # Drop None-only smart_details to keep payload small
    if body.get("smart_details") is None:
        body.pop("smart_details", None)
    r = requests.post(api("/runtime/heartbeat"), json=body, timeout=15)
    if r.status_code == 401:
        print("[heartbeat] unauthorized — re-enrolling")
        ident.update(enroll())
        body["agent_id"], body["agent_token"] = ident["agent_id"], ident["agent_token"]
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


def poll_enterprise_commands(ident: dict) -> list:
    try:
        r = requests.get(
            api(f"/agent/{enterprise_agent_id(ident)}/commands"),
            params={"agent_token": ident["agent_token"]},
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"[enterprise-command] poll transport error: {exc}")
        return []
    if r.status_code == 404:
        return []
    if 500 <= r.status_code < 600:
        print(f"[enterprise-command] server error {r.status_code}; retrying next cycle")
        return []
    if r.status_code in (401, 403):
        print(f"[enterprise-command] authorization error {r.status_code}; retrying next cycle")
        return []
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("commands", [])


def mark_enterprise_command_sent(ident: dict, command_id: str) -> None:
    r = requests.post(
        api(f"/agent/{enterprise_agent_id(ident)}/commands/{command_id}/sent"),
        params={"agent_token": ident["agent_token"]},
        timeout=15,
    )
    r.raise_for_status()


def post_enterprise_result(ident: dict, command_id: str, result: dict) -> None:
    agent_id = enterprise_agent_id(ident)
    endpoint = "completed" if int(result.get("exit_code", 1)) == 0 else "failed"
    payload = (
        result
        if endpoint == "completed"
        else {"message": result.get("stderr") or result.get("stdout") or "remote command failed"}
    )
    r = requests.post(
        api(f"/agent/{agent_id}/commands/{command_id}/{endpoint}"),
        params={"agent_token": ident["agent_token"]},
        json=payload,
        timeout=15,
    )
    r.raise_for_status()


def enterprise_agent_id(ident: dict) -> str:
    return str(os.getenv("BHUDI_ENTERPRISE_AGENT_ID") or ident["agent_id"])


def is_interactive_remote_session(command: dict) -> bool:
    command_type = str(command.get("command_type") or "")
    payload = command.get("payload") or {}
    return command_type == "remote.desktop.start" or (
        command_type == "remote.terminal.start" and payload.get("interactive", True)
    )


def execute(command: str, shell: bool = True) -> dict:
    try:
        completed = subprocess.run(
            command, shell=shell, capture_output=True, text=True, timeout=120
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


def poll_deployments(ident: dict) -> list:
    params: dict = {"hostname": agent_hostname()}
    device_id = os.getenv("BHUDI_DEVICE_ID")
    if device_id:
        params["device_id"] = device_id
    if ident.get("agent_id"):
        params["agent_id"] = ident["agent_id"]
    try:
        r = requests.get(api("/software-deployment/agent/pending"), params=params, timeout=15)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json().get("deployments") or []
    except Exception as e:
        print(f"[deploy] poll error: {e}")
        return []


def report_deployment(job_id: str, target_id: str, result: dict) -> None:
    body = {
        "status": result.get("status", "failed"),
        "exit_code": result.get("exit_code"),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
        "error_message": result.get("error_message"),
        "download_bytes": result.get("download_bytes"),
        "duration_ms": result.get("duration_ms"),
        "reboot_required": bool(result.get("reboot_required")),
    }
    r = requests.post(
        api(f"/software-deployment/jobs/{job_id}/targets/{target_id}/report"),
        json=body,
        timeout=30,
    )
    r.raise_for_status()


def process_deployments(ident: dict) -> None:
    deployments = poll_deployments(ident)
    for dep in deployments:
        job_id, target_id = str(dep.get("job_id") or ""), str(dep.get("target_id") or "")

        def _progress(partial: dict) -> None:
            try:
                report_deployment(job_id, target_id, partial)
            except Exception as e:
                print(f"[deploy] progress report failed: {e}")

        result = execute_deployment(dep, report=_progress)
        try:
            report_deployment(job_id, target_id, result)
        except Exception as e:
            print(f"[deploy] final report failed: {e}")


def report_endpoint_security() -> None:
    try:
        scan = scan_endpoint_security()
    except Exception as exc:
        print(f"[endpoint-security] scan failed: {exc}")
        return

    device_id = os.getenv("BHUDI_DEVICE_ID") or None
    payloads = to_ingest_payloads(scan, device_id=device_id)
    reported = 0
    for payload in payloads:
        if payload.get("device_id") and len(str(payload["device_id"])) < 32:
            payload["device_id"] = None
        try:
            r = requests.post(api("/endpoint-security/ingest/agent"), json=payload, timeout=20)
            if r.status_code in (200, 201):
                reported += 1
            else:
                print(
                    f"[endpoint-security] ingest {payload.get('provider_key')}: "
                    f"HTTP {r.status_code} {r.text[:200]}"
                )
        except Exception as exc:
            print(f"[endpoint-security] ingest error {payload.get('provider_key')}: {exc}")

    summary = scan.get("summary") or {}
    print(
        f"[endpoint-security] scanned products={len(payloads)} "
        f"installed={summary.get('total_detected', 0)} "
        f"healthy={summary.get('healthy', 0)} reported={reported}"
    )


def execute_enterprise_command(command: dict) -> dict:
    command_type = str(command.get("command_type") or "")
    payload = command.get("payload") or {}
    if command_type in {
        "inventory",
        "processes",
        "services",
        "software",
        "windows_updates",
        "event_logs",
        "network",
        "disks",
        "printers",
        "remote_script",
        "remote_powershell",
        "endpoint_security",
        "endpoint-security",
        "security_scan",
        "av_scan",
    }:
        return execute_named(command_type, payload)
    if is_interactive_remote_session(command):
        return streaming_session_coordinator.start(
            server_url=server_url(),
            agent_id=enterprise_agent_id(_CURRENT_IDENTITY),
            command=command,
        )
    return execute_command_record(command)


_CURRENT_IDENTITY: dict = {}


def run_once(ident: dict) -> None:
    global _CURRENT_IDENTITY, _security_cycle, _hardware_cycle
    _CURRENT_IDENTITY = ident

    _hardware_cycle += 1
    include_hw = _hardware_cycle >= HARDWARE_SENSOR_EVERY
    if include_hw:
        _hardware_cycle = 0

    hb = send_heartbeat(ident, include_hardware=include_hw)
    print(
        f"[heartbeat] ok pending={hb.get('pending_commands', 0)} "
        f"health={hb.get('health_score')} grade={hb.get('health_grade')} "
        f"alerts={hb.get('alerts_raised', 0)}"
    )

    for command in poll_enterprise_commands(ident):
        command_id = command.get("command_id") or command.get("id")
        if not command_id:
            continue
        print(f"[enterprise-command] {command_id}: {command.get('command_type')}")
        try:
            mark_enterprise_command_sent(ident, str(command_id))
            result = execute_enterprise_command(command)
            post_enterprise_result(ident, str(command_id), result)
            print(f"[enterprise-result] exit={result.get('exit_code')}")
        except Exception as exc:
            print(f"[enterprise-command] processing failed: {exc}")

    try:
        for cmd in poll_commands(ident):
            print(f"[command] {cmd['command_id']}: {cmd['command']}")
            result = execute(cmd["command"], shell=cmd.get("shell", True))
            post_result(ident, cmd["command_id"], result)
            print(f"[result] exit={result['exit_code']}")
    except Exception as exc:
        print(f"[command] poll/process failed: {exc}")

    try:
        process_deployments(ident)
    except Exception as exc:
        print(f"[deploy] cycle failed: {exc}")

    _security_cycle += 1
    if _security_cycle >= SECURITY_SCAN_EVERY:
        _security_cycle = 0
        try:
            report_endpoint_security()
        except Exception as exc:
            print(f"[endpoint-security] cycle failed: {exc}")


def main() -> None:
    print(f"[bhudi-agent] server={server_url()}")
    ident = load_identity()
    print(f"[bhudi-agent] agent_id={ident['agent_id']} host={agent_hostname()}")
    interval = int(os.getenv("BHUDI_HEARTBEAT_INTERVAL", "10"))
    try:
        report_endpoint_security()
    except Exception as exc:
        print(f"[endpoint-security] initial scan failed: {exc}")
    # Initial hardware sensor pass
    try:
        send_heartbeat(ident, include_hardware=True)
    except Exception as exc:
        print(f"[hardware] initial sensor pass failed: {exc}")
    while True:
        try:
            run_once(ident)
        except Exception as exc:
            print(f"[error] {exc}")
        if os.getenv("BHUDI_RUN_ONCE", "0").lower() in {"1", "true", "yes"}:
            return
        time.sleep(interval)


if __name__ == "__main__":
    main()
