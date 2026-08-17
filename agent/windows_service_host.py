"""Native Windows Service host for BhudiAgent.

Uses the Windows Service Control Manager directly via ctypes so the service
has no dependency on pywin32's pythonservice.exe bootstrap.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

SERVICE_NAME = "BhudiAgent"
SERVICE_DISPLAY_NAME = "Bhudi RMM Agent"
ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "agent-service.log"
AGENT = ROOT / "bhudi_agent.py"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)

SERVICE_WIN32_OWN_PROCESS = 0x00000010
SERVICE_RUNNING = 0x00000004
SERVICE_STOPPED = 0x00000001
SERVICE_START_PENDING = 0x00000002
SERVICE_STOP_PENDING = 0x00000003
SERVICE_ACCEPT_STOP = 0x00000001
SERVICE_CONTROL_STOP = 0x00000001

class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", wintypes.DWORD),
        ("dwCurrentState", wintypes.DWORD),
        ("dwControlsAccepted", wintypes.DWORD),
        ("dwWin32ExitCode", wintypes.DWORD),
        ("dwServiceSpecificExitCode", wintypes.DWORD),
        ("dwCheckPoint", wintypes.DWORD),
        ("dwWaitHint", wintypes.DWORD),
    ]

HANDLER = ctypes.WINFUNCTYPE(None, wintypes.DWORD)
MAIN = ctypes.WINFUNCTYPE(None, wintypes.DWORD, ctypes.POINTER(ctypes.c_wchar_p))

advapi32.RegisterServiceCtrlHandlerW.argtypes = [wintypes.LPCWSTR, HANDLER]
advapi32.RegisterServiceCtrlHandlerW.restype = wintypes.SC_HANDLE
advapi32.SetServiceStatus.argtypes = [wintypes.SC_HANDLE, ctypes.POINTER(SERVICE_STATUS)]
advapi32.SetServiceStatus.restype = wintypes.BOOL
advapi32.StartServiceCtrlDispatcherW.argtypes = [ctypes.c_void_p]
advapi32.StartServiceCtrlDispatcherW.restype = wintypes.BOOL

stop_event = threading.Event()
service_handle = None
agent_process: subprocess.Popen[str] | None = None


def log(message: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def report(state: int, accepted: int = 0, exit_code: int = 0, checkpoint: int = 0, wait_hint: int = 0) -> None:
    status = SERVICE_STATUS(SERVICE_WIN32_OWN_PROCESS, state, accepted, exit_code, 0, checkpoint, wait_hint)
    if service_handle:
        advapi32.SetServiceStatus(service_handle, ctypes.byref(status))


@HANDLER
def control_handler(control: int) -> None:
    if control == SERVICE_CONTROL_STOP:
        log("service stop requested")
        report(SERVICE_STOP_PENDING, 0, 0, 1, 10000)
        stop_event.set()
        if agent_process and agent_process.poll() is None:
            try:
                agent_process.terminate()
            except Exception as exc:
                log(f"agent terminate failed: {type(exc).__name__}: {exc}")


@MAIN
def service_main(argc: int, argv) -> None:
    global service_handle, agent_process
    service_handle = advapi32.RegisterServiceCtrlHandlerW(SERVICE_NAME, control_handler)
    if not service_handle:
        log(f"RegisterServiceCtrlHandler failed: {ctypes.get_last_error()}")
        return
    report(SERVICE_START_PENDING, 0, 0, 1, 15000)
    log(f"service starting; root={ROOT}; python={PYTHON}")
    try:
        if not PYTHON.exists():
            raise FileNotFoundError(PYTHON)
        if not AGENT.exists():
            raise FileNotFoundError(AGENT)

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["BHUDI_CONFIG_PATH"] = str(ROOT / "agent_config.json")
        env["BHUDI_IDENTITY_PATH"] = str(ROOT / "agent_identity.json")
        env["BHUDI_HOSTNAME"] = os.environ.get("COMPUTERNAME", "unknown")
        env.setdefault("BHUDI_HEARTBEAT_INTERVAL", "30")

        report(SERVICE_RUNNING, SERVICE_ACCEPT_STOP)
        log(f"launching agent: {PYTHON} {AGENT}")
        agent_process = subprocess.Popen(
            [str(PYTHON), str(AGENT)],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert agent_process.stdout is not None
        while not stop_event.is_set():
            line = agent_process.stdout.readline()
            if line:
                log(f"[agent] {line.rstrip()}")
            elif agent_process.poll() is not None:
                break
        if agent_process.poll() is None:
            agent_process.terminate()
            try:
                agent_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                agent_process.kill()
        remaining = agent_process.stdout.read() if agent_process.stdout else ""
        if remaining:
            for line in remaining.splitlines():
                log(f"[agent] {line}")
        log(f"agent exited with code {agent_process.returncode}")
        report(SERVICE_STOPPED)
    except Exception as exc:
        log(f"service startup/runtime failure: {type(exc).__name__}: {exc}")
        report(SERVICE_STOPPED, 0, 1)


def run_service() -> int:
    # The SCM supplies this table when starting the service.
    table_type = type("SERVICE_TABLE_ENTRY", (ctypes.Structure,), {
        "_fields_": [("lpServiceName", wintypes.LPWSTR), ("lpServiceProc", MAIN)]
    })
    table = (table_type * 2)()
    table[0].lpServiceName = SERVICE_NAME
    table[0].lpServiceProc = service_main
    # ctypes does not accept None directly for a function-pointer field.
    # Cast a NULL pointer to the callback type for the required terminator.
    table[1].lpServiceName = None
    table[1].lpServiceProc = ctypes.cast(None, MAIN)
    ok = advapi32.StartServiceCtrlDispatcherW(ctypes.byref(table))
    if not ok:
        error = ctypes.get_last_error()
        # 1063 means this executable was not launched by SCM; useful for debug.
        log(f"StartServiceCtrlDispatcher failed: {error}")
        return error
    return 0


if __name__ == "__main__":
    sys.exit(run_service())
