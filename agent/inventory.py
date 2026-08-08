"""Cross-platform, read-only endpoint inventory collectors for Bhudi."""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None


def _run(command: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as exc:
        return 1, "", str(exc)


def _disk_rows() -> list[dict[str, Any]]:
    rows = []
    if psutil:
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                rows.append({"device": part.device, "mountpoint": part.mountpoint, "filesystem": part.fstype, "total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent})
            except (OSError, PermissionError):
                continue
    return rows


def inventory() -> dict[str, Any]:
    data: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "disks": _disk_rows(),
    }
    if psutil:
        try:
            vm = psutil.virtual_memory()
            data["memory"] = {"total": vm.total, "available": vm.available, "used": vm.used, "percent": vm.percent}
            data["boot_time"] = psutil.boot_time()
        except Exception:
            pass
    return data


def processes() -> list[dict[str, Any]]:
    if psutil:
        rows = []
        for p in psutil.process_iter(["pid", "name", "username", "status", "cpu_percent", "memory_percent", "create_time"]):
            try:
                rows.append(p.info)
            except Exception:
                continue
        return rows
    code, stdout, _ = _run(["tasklist"] if os.name == "nt" else ["ps", "-eo", "pid,comm,user,state"])
    return [{"raw": stdout}] if code == 0 else []


def services() -> dict[str, Any]:
    if os.name == "nt":
        code, out, err = _run(["sc", "query", "type=", "service", "state=", "all"])
    elif shutil.which("systemctl"):
        code, out, err = _run(["systemctl", "list-units", "--type=service", "--all", "--no-pager"])
    else:
        code, out, err = _run(["launchctl", "list"] if platform.system() == "Darwin" else ["service", "--status-all"])
    return {"exit_code": code, "output": out, "error": err}


def software() -> dict[str, Any]:
    if os.name == "nt":
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*,HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher,InstallDate | ConvertTo-Json -Compress"]
    elif platform.system() == "Darwin":
        command = ["system_profiler", "SPApplicationsDataType", "-json"]
    elif shutil.which("dpkg-query"):
        command = ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"]
    elif shutil.which("rpm"):
        command = ["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\n"]
    else:
        return {"exit_code": 1, "output": "", "error": "No supported package inventory provider found"}
    code, out, err = _run(command, timeout=120)
    return {"exit_code": code, "output": out, "error": err}


def updates() -> dict[str, Any]:
    if os.name == "nt":
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-HotFix | Select-Object HotFixID,Description,InstalledOn,InstalledBy | ConvertTo-Json -Compress"]
    elif shutil.which("apt"): command = ["apt", "list", "--upgradable"]
    elif shutil.which("dnf"): command = ["dnf", "check-update"]
    elif shutil.which("softwareupdate"): command = ["softwareupdate", "-l"]
    else: return {"exit_code": 1, "output": "", "error": "No supported update provider found"}
    code, out, err = _run(command, timeout=120)
    return {"exit_code": code, "output": out, "error": err}


def event_logs(limit: int = 100, log_name: str = "Application") -> dict[str, Any]:
    limit = max(1, min(limit, 500))
    if os.name == "nt":
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Get-WinEvent -LogName '{log_name}' -MaxEvents {limit} | Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message | ConvertTo-Json -Compress"]
    elif shutil.which("journalctl"):
        command = ["journalctl", "-n", str(limit), "--no-pager", "-o", "json"]
    elif platform.system() == "Darwin":
        command = ["log", "show", "--last", "1h", "--style", "json"]
    else: return {"exit_code": 1, "output": "", "error": "No supported event log provider found"}
    code, out, err = _run(command, timeout=120)
    return {"exit_code": code, "output": out, "error": err}


def network() -> dict[str, Any]:
    data: dict[str, Any] = {"hostname": socket.gethostname(), "interfaces": [], "routes": []}
    if psutil:
        for name, addrs in psutil.net_if_addrs().items():
            data["interfaces"].append({"name": name, "addresses": [{"family": str(a.family), "address": a.address, "netmask": a.netmask, "broadcast": a.broadcast} for a in addrs]})
        try: data["stats"] = {k: v._asdict() for k, v in psutil.net_if_stats().items()}
        except Exception: pass
        try: data["connections"] = [{"fd": c.fd, "family": str(c.family), "type": str(c.type), "local": str(c.laddr), "remote": str(c.raddr), "status": c.status} for c in psutil.net_connections(kind="inet")]
        except Exception: pass
    return data


def printers() -> dict[str, Any]:
    if os.name == "nt":
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-Printer | Select-Object Name,DriverName,PortName,PrinterStatus,Default,Shared,Published | ConvertTo-Json -Compress"]
    elif shutil.which("lpstat"):
        command = ["lpstat", "-p", "-d", "-v"]
    else:
        return {"exit_code": 1, "output": "", "error": "No supported printer provider found"}
    code, out, err = _run(command, timeout=60)
    return {"exit_code": code, "output": out, "error": err}
