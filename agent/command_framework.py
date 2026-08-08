"""Dispatch named Bhudi commands to explicit agent capabilities."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from .inventory import event_logs, inventory, network, printers, processes, services, software, updates
except ImportError:
    from inventory import event_logs, inventory, network, printers, processes, services, software, updates


def _result(exit_code: int, stdout: str = "", stderr: str = "", **metadata: Any) -> dict[str, Any]:
    result = {"exit_code": exit_code, "stdout": stdout[:50000], "stderr": stderr[:20000]}
    if metadata:
        result["metadata"] = metadata
    return result


def _run(command: list[str], timeout: int = 300, cwd: str | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return _result(p.returncode, p.stdout or "", p.stderr or "")
    except subprocess.TimeoutExpired:
        return _result(124, stderr="command timed out")
    except Exception as exc:
        return _result(1, stderr=str(exc))


def _json_result(data: Any) -> dict[str, Any]:
    return _result(0, stdout=json.dumps(data, default=str), data=data)


def execute_named(command_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    name = command_type.strip().lower()

    if name == "inventory": return _json_result(inventory())
    if name == "processes": return _json_result(processes())
    if name == "services": return _json_result(services())
    if name == "software": return _json_result(software())
    if name == "windows_updates": return _json_result(updates())
    if name == "event_logs": return _json_result(event_logs(int(payload.get("limit", 100)), str(payload.get("log_name", "Application"))))
    if name == "network": return _json_result(network())
    if name == "disks": return _json_result(inventory().get("disks", []))
    if name == "printers": return _json_result(printers())

    if name == "remote_powershell":
        command = str(payload.get("command") or "").strip()
        if not command: return _result(1, stderr="command is required")
        executable = "powershell.exe" if os.name == "nt" else "pwsh"
        return _run([executable, "-NoProfile", "-NonInteractive", "-Command", command, *(payload.get("arguments") or [])], int(payload.get("timeout_seconds", 300)))

    if name == "remote_script":
        script = str(payload.get("script") or "")
        interpreter = str(payload.get("interpreter") or ("powershell" if os.name == "nt" else "bash")).lower()
        if not script: return _result(1, stderr="script is required")
        suffix = ".ps1" if interpreter in {"powershell", "pwsh"} else ".sh"
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as handle:
            handle.write(script)
            path = handle.name
        try:
            if interpreter in {"powershell", "pwsh"}:
                executable = "powershell.exe" if os.name == "nt" else "pwsh"
                command = [executable, "-NoProfile", "-NonInteractive", "-File", path]
            elif interpreter in {"bash", "sh"}:
                command = [interpreter, path]
            elif interpreter == "python":
                command = ["python", path]
            else:
                return _result(1, stderr=f"unsupported script interpreter: {interpreter}")
            return _run(command, int(payload.get("timeout_seconds", 300)), payload.get("working_directory"))
        finally:
            Path(path).unlink(missing_ok=True)

    return _result(1, stderr=f"unsupported named command: {command_type}")
