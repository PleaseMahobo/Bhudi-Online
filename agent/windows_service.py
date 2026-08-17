"""Bhudi RMM Windows Service wrapper.

Installs/runs the existing bhudi_agent.py loop as a native Windows service
using pywin32. The service itself owns lifecycle/restart control; the agent
continues to own enrollment, heartbeat, command and telemetry behavior.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil


SERVICE_NAME = "BhudiAgent"
SERVICE_DISPLAY_NAME = "Bhudi RMM Agent"
SERVICE_DESCRIPTION = "Bhudi remote monitoring, management and security agent."
ROOT = Path(__file__).resolve().parent


class BhudiAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION
    _svc_start_type_ = win32service.SERVICE_AUTO_START

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process: subprocess.Popen[str] | None = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        win32event.SetEvent(self.stop_event)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg(f"{SERVICE_NAME} starting")
        self.main()

    def main(self):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env.setdefault("BHUDI_CONFIG_PATH", str(ROOT / "agent_config.json"))
        env.setdefault("BHUDI_IDENTITY_PATH", str(ROOT / "agent_identity.json"))
        env.setdefault("BHUDI_HOSTNAME", os.environ.get("COMPUTERNAME", "unknown"))
        env.setdefault("BHUDI_HEARTBEAT_INTERVAL", "30")
        log_path = ROOT / "agent-service.log"
        ROOT.mkdir(parents=True, exist_ok=True)

        while True:
            if win32event.WaitForSingleObject(self.stop_event, 0) == win32event.WAIT_OBJECT_0:
                return
            try:
                with log_path.open("a", encoding="utf-8") as log:
                    self.process = subprocess.Popen(
                        [sys.executable, str(ROOT / "bhudi_agent.py")],
                        cwd=str(ROOT),
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                while self.process.poll() is None:
                    if win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_OBJECT_0:
                        self.SvcStop()
                        return
                self.process = None
            except Exception as exc:
                try:
                    servicemanager.LogErrorMsg(f"{SERVICE_NAME}: {exc}")
                except Exception:
                    pass
            if win32event.WaitForSingleObject(self.stop_event, 10000) == win32event.WAIT_OBJECT_0:
                return


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(BhudiAgentService)
