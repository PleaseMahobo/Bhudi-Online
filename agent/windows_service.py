"""Bhudi RMM Windows Service wrapper."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

SERVICE_NAME = "BhudiAgent"
SERVICE_DISPLAY_NAME = "Bhudi RMM Agent"
SERVICE_DESCRIPTION = "Bhudi remote monitoring, management and security agent."
ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
LOG_PATH = ROOT / "agent-service.log"


def log(message: str) -> None:
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
            fh.flush()
    except Exception:
        pass


class BhudiAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION
    _svc_start_type_ = win32service.SERVICE_AUTO_START

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process: subprocess.Popen | None = None

    def SvcStop(self):
        log("service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        win32event.SetEvent(self.stop_event)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        log("service stopped")

    def SvcDoRun(self):
        log(f"service starting; root={ROOT}; python={VENV_PYTHON}")
        try:
            servicemanager.LogInfoMsg(f"{SERVICE_NAME} starting")
            self.main()
        except Exception as exc:
            log(f"service startup failure: {type(exc).__name__}: {exc}")
            try:
                servicemanager.LogErrorMsg(f"{SERVICE_NAME} startup failure: {exc}")
            except Exception:
                pass
            raise

    def main(self):
        if not VENV_PYTHON.exists():
            raise FileNotFoundError(f"Agent interpreter not found: {VENV_PYTHON}")
        agent_script = ROOT / "bhudi_agent.py"
        if not agent_script.exists():
            raise FileNotFoundError(f"Agent script not found: {agent_script}")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["BHUDI_CONFIG_PATH"] = str(ROOT / "agent_config.json")
        env["BHUDI_IDENTITY_PATH"] = str(ROOT / "agent_identity.json")
        env["BHUDI_HOSTNAME"] = os.environ.get("COMPUTERNAME", "unknown")
        env.setdefault("BHUDI_HEARTBEAT_INTERVAL", "30")

        # Keep the service process alive while the supervised agent is running.
        # The pywin32 service framework reports the service state before entering
        # this loop, so SCM does not wait for the agent's network startup.
        while True:
            if win32event.WaitForSingleObject(self.stop_event, 0) == win32event.WAIT_OBJECT_0:
                return
            log(f"launching agent: {VENV_PYTHON} {agent_script}")
            try:
                self.process = subprocess.Popen(
                    [str(VENV_PYTHON), str(agent_script)],
                    cwd=str(ROOT),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert self.process.stdout is not None
                while self.process.poll() is None:
                    line = self.process.stdout.readline()
                    if line:
                        log(f"[agent] {line.rstrip()}")
                    if win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_OBJECT_0:
                        self.SvcStop()
                        return
                remaining = self.process.stdout.read()
                if remaining:
                    for line in remaining.splitlines():
                        log(f"[agent] {line}")
                exit_code = self.process.returncode
                self.process = None
                log(f"agent exited with code {exit_code}; restarting in 10s")
            except Exception as exc:
                self.process = None
                log(f"agent launch failure: {type(exc).__name__}: {exc}")
            if win32event.WaitForSingleObject(self.stop_event, 10000) == win32event.WAIT_OBJECT_0:
                return


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(BhudiAgentService)
