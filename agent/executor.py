from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None


def _platform_family(platform_name: str | None = None) -> str:
    name = (platform_name or sys.platform or "").lower()
    if name.startswith("win"):
        return "windows"
    if name.startswith("darwin") or name.startswith("mac"):
        return "macos"
    if name.startswith("linux"):
        return "linux"
    return "unknown"


def _result(exit_code: int, stdout: str = "", stderr: str = "", **metadata: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "exit_code": exit_code,
        "stdout": stdout[:50000],
        "stderr": stderr[:20000],
    }
    if metadata:
        payload["metadata"] = metadata
    return payload


def _run_subprocess(command: list[str] | str, *, shell: bool = False, timeout_seconds: int = 300, cwd: str | None = None) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=cwd,
        )
        return _result(completed.returncode, completed.stdout or "", completed.stderr or "")
    except subprocess.TimeoutExpired:
        return _result(124, stderr="command timed out")
    except FileNotFoundError as exc:
        return _result(127, stderr=str(exc))
    except Exception as exc:
        return _result(1, stderr=str(exc))


def _resolve_shell(shell_name: str | None, platform_name: str) -> str:
    family = _platform_family(platform_name)
    requested = (shell_name or "").strip().lower()
    if requested:
        if requested == "powershell":
            return shutil.which("powershell") or shutil.which("pwsh") or "powershell"
        if requested == "cmd":
            return shutil.which("cmd") or "cmd"
        if requested in {"bash", "zsh", "sh"}:
            path = shutil.which(requested)
            if path:
                return path
            return f"/bin/{requested}"
        return requested

    if family == "windows":
        return shutil.which("powershell") or shutil.which("pwsh") or "powershell"
    if family == "macos":
        return shutil.which("zsh") or "/bin/zsh"
    if family == "linux":
        return shutil.which("bash") or "/bin/bash"
    return shutil.which("sh") or "/bin/sh"


def _ensure_supported(families: set[str], platform_name: str, feature: str) -> str | None:
    family = _platform_family(platform_name)
    if family not in families:
        return f"{feature} is not supported on {family}"
    return None


def _handle_remote_desktop(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    family = _platform_family(platform_name)
    transport = payload.get("display_protocol") or ("rdp" if family == "windows" else "vnc")
    return _result(
        0,
        stdout=f"Prepared {transport} remote desktop session in {payload.get('session_mode', 'control')} mode",
        platform=family,
        session_mode=payload.get("session_mode", "control"),
        display_protocol=transport,
        consent_required=bool(payload.get("consent_required", False)),
        interactive=True,
    )


def _handle_remote_terminal(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    shell_path = _resolve_shell(str(payload.get("shell") or ""), platform_name)
    return _result(
        0,
        stdout=f"Remote terminal ready with {shell_path}",
        platform=_platform_family(platform_name),
        shell=shell_path,
        working_directory=payload.get("working_directory") or os.getcwd(),
        interactive=bool(payload.get("interactive", True)),
        environment_keys=sorted((payload.get("environment") or {}).keys()),
    )


def _handle_file_browser(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    operation = str(payload.get("operation") or "list")
    path = Path(str(payload.get("path") or "")).expanduser()

    if operation == "list":
        if not path.exists() or not path.is_dir():
            return _result(1, stderr=f"directory not found: {path}")
        entries = [
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.exists() else 0,
            }
            for entry in sorted(path.iterdir(), key=lambda item: item.name.lower())
        ]
        return _result(0, stdout=json.dumps(entries), platform=_platform_family(platform_name), entries=entries)

    if operation == "stat":
        if not path.exists():
            return _result(1, stderr=f"path not found: {path}")
        stat = path.stat()
        info = {"path": str(path), "is_dir": path.is_dir(), "size": stat.st_size}
        return _result(0, stdout=json.dumps(info), platform=_platform_family(platform_name), stat=info)

    if operation == "mkdir":
        path.mkdir(parents=bool(payload.get("recursive", False)), exist_ok=True)
        return _result(0, stdout=f"created directory {path}", platform=_platform_family(platform_name), path=str(path))

    if operation == "delete":
        if path.is_dir():
            if payload.get("recursive"):
                shutil.rmtree(path)
            else:
                path.rmdir()
        elif path.exists():
            path.unlink()
        else:
            return _result(1, stderr=f"path not found: {path}")
        return _result(0, stdout=f"deleted {path}", platform=_platform_family(platform_name), path=str(path))

    if operation == "upload":
        content_b64 = payload.get("content_b64")
        if not content_b64:
            return _result(1, stderr="content_b64 is required for upload operations")
        if path.exists() and not payload.get("overwrite"):
            return _result(1, stderr=f"refusing to overwrite existing file: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(str(content_b64)))
        return _result(0, stdout=f"uploaded {path}", platform=_platform_family(platform_name), path=str(path), bytes_written=path.stat().st_size)

    if operation == "download":
        if not path.exists() or path.is_dir():
            return _result(1, stderr=f"file not found: {path}")
        destination_path = payload.get("destination_path")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        metadata: dict[str, Any] = {
            "path": str(path),
            "content_b64": encoded,
            "size": path.stat().st_size,
            "platform": _platform_family(platform_name),
        }
        if destination_path:
            destination = Path(str(destination_path)).expanduser()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            metadata["destination_path"] = str(destination)
        return _result(0, stdout=f"downloaded {path}", **metadata)

    return _result(1, stderr=f"unsupported file browser operation: {operation}")


def _handle_registry(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    unsupported = _ensure_supported({"windows"}, platform_name, "Registry editor")
    if unsupported:
        return _result(1, stderr=unsupported)
    try:
        import winreg  # type: ignore
    except ImportError:
        return _result(1, stderr="winreg module unavailable")

    hive_name = str(payload.get("hive") or "HKLM")
    hive = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
        "HKU": winreg.HKEY_USERS,
        "HKCC": winreg.HKEY_CURRENT_CONFIG,
    }.get(hive_name)
    if hive is None:
        return _result(1, stderr=f"unsupported registry hive: {hive_name}")

    key_path = str(payload.get("key_path") or "")
    value_name = payload.get("value_name") or ""
    operation = str(payload.get("operation") or "get")
    access = winreg.KEY_READ if operation in {"get", "list"} else winreg.KEY_SET_VALUE

    try:
        if operation == "list":
            items: list[dict[str, Any]] = []
            with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        name, data, kind = winreg.EnumValue(key, index)
                        items.append({"name": name, "data": data, "type": kind})
                        index += 1
                    except OSError:
                        break
            return _result(0, stdout=json.dumps(items), items=items)

        with winreg.OpenKey(hive, key_path, 0, access) as key:
            if operation == "get":
                value, kind = winreg.QueryValueEx(key, str(value_name))
                return _result(0, stdout=json.dumps({"value": value, "type": kind}), value=value, value_type=kind)
            if operation == "delete":
                winreg.DeleteValue(key, str(value_name))
                return _result(0, stdout=f"deleted registry value {value_name}")
            if operation == "set":
                value_type = str(payload.get("value_type") or "string")
                reg_type = {
                    "string": winreg.REG_SZ,
                    "expand_string": winreg.REG_EXPAND_SZ,
                    "dword": winreg.REG_DWORD,
                    "qword": winreg.REG_QWORD,
                    "binary": winreg.REG_BINARY,
                    "multi_string": winreg.REG_MULTI_SZ,
                }.get(value_type)
                if reg_type is None:
                    return _result(1, stderr=f"unsupported registry value type: {value_type}")
                winreg.SetValueEx(key, str(value_name), 0, reg_type, payload.get("value_data"))
                return _result(0, stdout=f"updated registry value {value_name}")
    except FileNotFoundError:
        return _result(1, stderr=f"registry path not found: {hive_name}\\{key_path}")
    except OSError as exc:
        return _result(1, stderr=str(exc))

    return _result(1, stderr=f"unsupported registry operation: {operation}")


def _process_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if psutil is None:
        return rows
    for process in psutil.process_iter(["pid", "name", "username", "status"]):
        try:
            rows.append(process.info)
        except (psutil.Error, OSError):
            continue
    return rows


def _service_list(platform_name: str) -> dict[str, Any]:
    family = _platform_family(platform_name)
    if family == "windows":
        return _run_subprocess(["sc", "query", "type=", "service", "state=", "all"], timeout_seconds=120)
    if family == "linux":
        if shutil.which("systemctl"):
            return _run_subprocess(["systemctl", "list-units", "--type=service", "--all", "--no-pager"], timeout_seconds=120)
        return _run_subprocess(["service", "--status-all"], timeout_seconds=120)
    if family == "macos":
        return _run_subprocess(["launchctl", "list"], timeout_seconds=120)
    return _result(1, stderr=f"service listing is not supported on {family}")


def _service_action(platform_name: str, action: str, service_name: str) -> dict[str, Any]:
    family = _platform_family(platform_name)
    if family == "windows":
        mapped = "stop" if action == "stop_service" else "start"
        if action == "restart_service":
            stopped = _run_subprocess(["sc", "stop", service_name], timeout_seconds=120)
            if stopped["exit_code"] != 0:
                return stopped
            return _run_subprocess(["sc", "start", service_name], timeout_seconds=120)
        return _run_subprocess(["sc", mapped, service_name], timeout_seconds=120)
    if family == "linux":
        if shutil.which("systemctl"):
            mapped = {
                "start_service": "start",
                "stop_service": "stop",
                "restart_service": "restart",
            }[action]
            return _run_subprocess(["systemctl", mapped, service_name], timeout_seconds=120)
    if family == "macos":
        if action == "restart_service":
            return _result(1, stderr="restart_service is not supported for launchctl without a domain target")
        mapped = "bootstrap" if action == "start_service" else "bootout"
        return _run_subprocess(["launchctl", mapped, f"system/{service_name}"], timeout_seconds=120)
    return _result(1, stderr=f"service actions are not supported on {family}")


def _handle_task_manager(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    operation = str(payload.get("operation") or "list_processes")
    if operation == "list_processes":
        rows = _process_rows()
        if rows:
            return _result(0, stdout=json.dumps(rows), platform=_platform_family(platform_name), processes=rows)
        family = _platform_family(platform_name)
        if family == "windows":
            return _run_subprocess(["tasklist"], timeout_seconds=120)
        return _run_subprocess(["ps", "-eo", "pid,comm,user,state"], timeout_seconds=120)
    if operation == "list_services":
        return _service_list(platform_name)
    if operation == "terminate_process":
        pid = payload.get("process_id")
        image_name = payload.get("image_name")
        if psutil is not None and pid is not None:
            try:
                proc = psutil.Process(int(pid))
                proc.terminate()
                return _result(0, stdout=f"terminated process {pid}")
            except (psutil.Error, OSError) as exc:
                return _result(1, stderr=str(exc))
        family = _platform_family(platform_name)
        if family == "windows":
            if pid is not None:
                return _run_subprocess(["taskkill", "/PID", str(pid), "/F"], timeout_seconds=120)
            return _run_subprocess(["taskkill", "/IM", str(image_name), "/F"], timeout_seconds=120)
        if pid is not None:
            return _run_subprocess(["kill", "-TERM", str(pid)], timeout_seconds=120)
        return _run_subprocess(["pkill", "-f", str(image_name)], timeout_seconds=120)
    if operation in {"start_service", "stop_service", "restart_service"}:
        service_name = str(payload.get("service_name") or "")
        if not service_name:
            return _result(1, stderr="service_name is required")
        return _service_action(platform_name, operation, service_name)
    return _result(1, stderr=f"unsupported task manager operation: {operation}")


def _handle_powershell(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    command = str(payload.get("command") or "").strip()
    if not command:
        return _result(1, stderr="command is required")
    shell_path = shutil.which("powershell") or shutil.which("pwsh")
    if shell_path is None:
        return _result(1, stderr="PowerShell is not available on this device")
    return _run_subprocess(
        [shell_path, "-NoProfile", "-NonInteractive", "-Command", command, *(payload.get("arguments") or [])],
        timeout_seconds=int(payload.get("timeout_seconds") or 300),
        cwd=payload.get("working_directory"),
    )


def _handle_cmd(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    unsupported = _ensure_supported({"windows"}, platform_name, "Remote CMD")
    if unsupported:
        return _result(1, stderr=unsupported)
    command = str(payload.get("command") or "").strip()
    if not command:
        return _result(1, stderr="command is required")
    return _run_subprocess(
        [shutil.which("cmd") or "cmd", "/c", command, *(payload.get("arguments") or [])],
        timeout_seconds=int(payload.get("timeout_seconds") or 300),
        cwd=payload.get("working_directory"),
    )


def _handle_event_viewer(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    family = _platform_family(platform_name)
    log_name = str(payload.get("log_name") or "Application")
    limit = str(payload.get("limit") or 100)
    if family == "windows":
        shell_path = shutil.which("powershell") or shutil.which("pwsh")
        if shell_path is None:
            return _result(1, stderr="PowerShell is required for event log queries")
        query = f"Get-WinEvent -LogName '{log_name}' -MaxEvents {limit} | Select-Object -First {limit} | Format-List -Property TimeCreated,Id,LevelDisplayName,ProviderName,Message"
        return _run_subprocess([shell_path, "-NoProfile", "-NonInteractive", "-Command", query], timeout_seconds=300)
    if family == "linux":
        if shutil.which("journalctl"):
            return _run_subprocess(["journalctl", "-n", limit, "--no-pager"], timeout_seconds=300)
        return _result(1, stderr="journalctl is not available on this device")
    if family == "macos":
        return _run_subprocess(["log", "show", "--last", "1h", "--style", "compact"], timeout_seconds=300)
    return _result(1, stderr=f"event viewer is not supported on {family}")


def _handle_wake_on_lan(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    mac_address = str(payload.get("mac_address") or "").replace(":", "").replace("-", "")
    if len(mac_address) != 12:
        return _result(1, stderr="mac_address must contain 12 hexadecimal characters")
    packet = bytes.fromhex("FF" * 6 + mac_address * 16)
    broadcast_address = str(payload.get("broadcast_address") or "255.255.255.255")
    port = int(payload.get("port") or 9)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (broadcast_address, port))
        return _result(0, stdout=f"sent Wake-on-LAN packet to {broadcast_address}:{port}", mac_address=mac_address, platform=_platform_family(platform_name))
    except OSError as exc:
        return _result(1, stderr=str(exc))


def _power_action_result(command: str, platform_name: str, allow_execution: bool) -> dict[str, Any]:
    if not allow_execution:
        return _result(0, stdout=f"dry-run: {command}", platform=_platform_family(platform_name), simulated=True, command=command)
    return _run_subprocess(command, shell=True, timeout_seconds=120)


def _handle_reboot(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    family = _platform_family(platform_name)
    delay = int(payload.get("delay_seconds") or 0)
    allow_execution = os.getenv("BHUDI_ALLOW_POWER_ACTIONS", "0") == "1"
    if family == "windows":
        command = f"shutdown /r {'/f ' if payload.get('force', True) else ''}/t {delay}"
        if payload.get("message"):
            command += f' /c "{payload["message"]}"'
        return _power_action_result(command, platform_name, allow_execution)
    if family == "linux":
        return _power_action_result(f"shutdown -r +{max(delay // 60, 0)}", platform_name, allow_execution)
    if family == "macos":
        return _power_action_result(f"osascript -e 'tell app \"System Events\" to restart'", platform_name, allow_execution)
    return _result(1, stderr=f"reboot is not supported on {family}")


def _handle_safe_mode_reboot(payload: dict[str, Any], platform_name: str) -> dict[str, Any]:
    unsupported = _ensure_supported({"windows"}, platform_name, "Safe mode reboot")
    if unsupported:
        return _result(1, stderr=unsupported)
    delay = int(payload.get("delay_seconds") or 0)
    networking = bool(payload.get("with_networking", True))
    mode = "network" if networking else "minimal"
    allow_execution = os.getenv("BHUDI_ALLOW_POWER_ACTIONS", "0") == "1"
    command = f"bcdedit /set {{current}} safeboot {mode} && shutdown /r {'/f ' if payload.get('force', True) else ''}/t {delay}"
    if payload.get("message"):
        command += f' /c "{payload["message"]}"'
    return _power_action_result(command, platform_name, allow_execution)


def execute_command_record(command: dict[str, Any], *, platform_name: str | None = None) -> dict[str, Any]:
    command_type = str(command.get("command_type") or "")
    payload = command.get("payload") or {}
    effective_platform = platform_name or sys.platform

    handlers = {
        "remote.desktop.start": _handle_remote_desktop,
        "remote.terminal.start": _handle_remote_terminal,
        "remote.file_browser": _handle_file_browser,
        "remote.registry": _handle_registry,
        "remote.task_manager": _handle_task_manager,
        "remote.powershell": _handle_powershell,
        "remote.cmd": _handle_cmd,
        "remote.event_viewer": _handle_event_viewer,
        "remote.wake_on_lan": _handle_wake_on_lan,
        "remote.reboot": _handle_reboot,
        "remote.safe_mode_reboot": _handle_safe_mode_reboot,
    }

    handler = handlers.get(command_type)
    if handler is not None:
        return handler(payload, effective_platform)

    raw_command = command.get("command")
    if isinstance(raw_command, str) and raw_command.strip():
        return _run_subprocess(raw_command, shell=bool(command.get("shell", True)), timeout_seconds=int(command.get("timeout_seconds") or 300))
    return _result(1, stderr=f"unsupported command type: {command_type or 'unknown'}")