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


def _CRITICAL_SMART_IDS() -> dict[int, str]:
    """Attribute IDs that predict failure (raw value > 0 is concerning)."""
    return {
        5: "reallocated_sectors",
        187: "reported_uncorrectable",
        197: "current_pending_sectors",
        198: "offline_uncorrectable",
        183: "runtime_bad_block",
        184: "end_to_end_error",
    }


def _INFO_SMART_IDS() -> dict[int, str]:
    """Useful context attributes (not necessarily failure predictors)."""
    return {
        9: "power_on_hours",
        12: "power_cycle_count",
        194: "temperature_celsius",
        190: "airflow_temperature",
        193: "load_cycle_count",
        1: "raw_read_error_rate",
        7: "seek_error_rate",
        10: "spin_retry_count",
        199: "udma_crc_error_count",
    }


def _parse_smartctl_json(data: dict, device: str, exit_code: int) -> dict:
    """Parse smartctl -H -A -j JSON into a structured disk entry."""
    entry: dict = {
        "device": device,
        "exit_code": exit_code,
        "status": "unknown",
        "model": data.get("model_name") or data.get("model_family"),
        "serial": data.get("serial_number"),
        "firmware": data.get("firmware_version"),
        "capacity_bytes": (data.get("user_capacity") or {}).get("bytes")
        if isinstance(data.get("user_capacity"), dict)
        else data.get("user_capacity"),
        "attributes": {},
        "critical": {},
        "warnings": [],
    }

    smart_status = data.get("smart_status")
    passed = None
    if isinstance(smart_status, dict):
        passed = smart_status.get("passed")
    if passed is True:
        entry["status"] = "ok"
    elif passed is False:
        entry["status"] = "failing"

    temp = None
    temp_obj = data.get("temperature")
    if isinstance(temp_obj, dict) and temp_obj.get("current") is not None:
        try:
            temp = float(temp_obj["current"])
        except (TypeError, ValueError):
            pass
    if temp is not None:
        entry["temperature_c"] = temp

    ata = data.get("ata_smart_attributes") or {}
    table = ata.get("table") if isinstance(ata, dict) else None
    critical_ids = _CRITICAL_SMART_IDS()
    info_ids = _INFO_SMART_IDS()

    if isinstance(table, list):
        for row in table:
            if not isinstance(row, dict):
                continue
            try:
                aid = int(row.get("id"))
            except (TypeError, ValueError):
                continue
            name = str(row.get("name") or f"id_{aid}")
            raw_obj = row.get("raw")
            raw_val = None
            if isinstance(raw_obj, dict):
                raw_val = raw_obj.get("value")
            elif raw_obj is not None:
                raw_val = raw_obj
            try:
                raw_int = int(raw_val) if raw_val is not None else None
            except (TypeError, ValueError):
                raw_int = None

            norm = row.get("value")
            worst = row.get("worst")
            thresh = row.get("thresh")
            when_failed = (row.get("when_failed") or "").strip()

            attr = {
                "id": aid,
                "name": name,
                "raw": raw_int,
                "value": int(norm) if norm is not None else None,
                "worst": int(worst) if worst is not None else None,
                "thresh": int(thresh) if thresh is not None else None,
            }
            if when_failed:
                attr["when_failed"] = when_failed

            key = critical_ids.get(aid) or info_ids.get(aid) or name.lower()
            entry["attributes"][key] = attr

            if temp is None and aid in (194, 190) and raw_int is not None:
                if 0 < raw_int < 120:
                    entry["temperature_c"] = float(raw_int)
                    temp = float(raw_int)

            if aid in critical_ids and raw_int is not None and raw_int > 0:
                entry["critical"][critical_ids[aid]] = raw_int
                entry["warnings"].append(
                    f"{critical_ids[aid]}={raw_int} (attr {aid})"
                )

            if when_failed and when_failed.lower() not in ("", "unknown"):
                entry["warnings"].append(f"{name} when_failed={when_failed}")
                if entry["status"] == "ok":
                    entry["status"] = "warning"

    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict):
        entry["protocol"] = "nvme"
        crit_warn = nvme.get("critical_warning")
        if crit_warn:
            entry["critical"]["nvme_critical_warning"] = crit_warn
            entry["warnings"].append(f"nvme_critical_warning={crit_warn}")
            if entry["status"] == "ok":
                entry["status"] = "warning"
        for k_src, k_dst in (
            ("available_spare", "available_spare_pct"),
            ("percentage_used", "percentage_used"),
            ("media_errors", "media_errors"),
            ("num_err_log_entries", "error_log_entries"),
            ("temperature", "temperature_c"),
        ):
            if nvme.get(k_src) is not None:
                entry["attributes"][k_dst] = {"raw": nvme.get(k_src), "name": k_src}
        if nvme.get("temperature") is not None and "temperature_c" not in entry:
            try:
                entry["temperature_c"] = float(nvme["temperature"])
            except (TypeError, ValueError):
                pass
        spare = nvme.get("available_spare")
        spare_thresh = nvme.get("available_spare_threshold")
        if spare is not None and spare_thresh is not None:
            try:
                if int(spare) < int(spare_thresh):
                    entry["critical"]["available_spare_low"] = int(spare)
                    entry["warnings"].append(
                        f"available_spare={spare}% below threshold {spare_thresh}%"
                    )
                    if entry["status"] == "ok":
                        entry["status"] = "warning"
            except (TypeError, ValueError):
                pass
        media_err = nvme.get("media_errors")
        if media_err is not None:
            try:
                if int(media_err) > 0:
                    entry["critical"]["media_errors"] = int(media_err)
                    entry["warnings"].append(f"media_errors={media_err}")
                    if entry["status"] in ("ok", "warning"):
                        entry["status"] = "failing" if int(media_err) > 10 else "warning"
            except (TypeError, ValueError):
                pass

    if entry["critical"] and entry["status"] == "ok":
        entry["status"] = "warning"

    if not entry["attributes"]:
        entry.pop("attributes", None)
    if not entry["critical"]:
        entry.pop("critical", None)
    if not entry["warnings"]:
        entry.pop("warnings", None)

    return entry


def _collect_smart_linux() -> tuple[str | None, dict | None]:
    """Linux: smartctl -H -A -j with critical attribute extraction."""
    details: dict = {"disks": [], "source": "smartctl"}

    devices: list[str] = []
    try:
        lsblk = subprocess.run(
            ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in (lsblk.stdout or "").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "disk":
                devices.append(f"/dev/{parts[0]}")
    except FileNotFoundError:
        pass
    except Exception as exc:
        details["lsblk_error"] = str(exc)

    if not devices:
        for candidate in ("/dev/sda", "/dev/nvme0n1", "/dev/vda"):
            if Path(candidate).exists():
                devices.append(candidate)
    if not devices:
        details["error"] = "no_block_devices"
        return None, details

    overall = "ok"
    rank = {"ok": 0, "unknown": 1, "warning": 2, "failing": 3, "unavailable": 1}

    for dev in devices[:6]:
        entry: dict = {"device": dev, "status": "unavailable"}
        try:
            r = subprocess.run(
                ["smartctl", "-H", "-A", "-j", "-n", "standby", dev],
                capture_output=True,
                text=True,
                timeout=20,
            )
            stdout = r.stdout or ""
            try:
                data = json.loads(stdout) if stdout.strip() else {}
            except json.JSONDecodeError:
                data = {}

            if data:
                entry = _parse_smartctl_json(data, dev, r.returncode)
            else:
                text_out = stdout + (r.stderr or "")
                if re.search(r"PASSED", text_out, re.I):
                    entry["status"] = "ok"
                elif re.search(r"FAILED|FAILING", text_out, re.I):
                    entry["status"] = "failing"
                else:
                    entry["status"] = "unknown"
                entry["exit_code"] = r.returncode
                if r.returncode == 2 or "STANDBY" in text_out.upper():
                    entry["status"] = "unknown"
                    entry["note"] = "drive_in_standby"
        except FileNotFoundError:
            details["error"] = "smartctl_not_found"
            return None, details
        except subprocess.TimeoutExpired:
            entry["status"] = "unknown"
            entry["note"] = "smartctl_timeout"
        except Exception as exc:
            entry["status"] = "unavailable"
            entry["error"] = str(exc)

        details["disks"].append(entry)
        st = entry.get("status") or "unknown"
        if rank.get(st, 0) > rank.get(overall, 0):
            overall = st

    if not details["disks"]:
        return None, details
    return overall, details


def _collect_smart_windows() -> tuple[str | None, dict | None]:
    """Windows: Get-PhysicalDisk health status."""
    details: dict = {"disks": [], "source": "Get-PhysicalDisk"}
    try:
        ps = (
            "Get-PhysicalDisk | Select-Object FriendlyName,HealthStatus,OperationalStatus,"
            "MediaType,Size,SerialNumber | ConvertTo-Json -Compress"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if r.returncode != 0 or not (r.stdout or "").strip():
            details["error"] = (r.stderr or "empty_output")[:300]
            return None, details

        data = json.loads(r.stdout)
        items = data if isinstance(data, list) else [data]
        overall = "ok"
        for item in items:
            health = str(item.get("HealthStatus") or "").lower()
            entry = {
                "device": item.get("FriendlyName"),
                "serial": item.get("SerialNumber"),
                "health": item.get("HealthStatus"),
                "operational": item.get("OperationalStatus"),
                "media": item.get("MediaType"),
                "capacity_bytes": item.get("Size"),
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
    return None, details


def _collect_smart() -> tuple[str | None, dict | None]:
    """Best-effort disk SMART health + critical attributes. Returns (status, details)."""
    if os.name == "nt":
        return _collect_smart_windows()
    return _collect_smart_linux()


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
        "agent_version": "1.5.0-smart-attrs",
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
