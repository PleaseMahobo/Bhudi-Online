from __future__ import annotations

import os
import threading
import time

from app.database.session import SessionLocal
from app.services.itsm_operational_service import ITSMOperationalService


class ITSMSLAWorker:
    def __init__(self) -> None:
        self.interval = max(30, int(os.getenv("ITSM_SLA_WORKER_INTERVAL_SECONDS", "60")))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> int:
        db = SessionLocal()
        try:
            return len(ITSMOperationalService(db).escalate_sla())
        finally:
            db.close()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                count = self.run_once()
                if count:
                    print(f"[itsm-sla-worker] processed {count} SLA escalation(s)")
            except Exception as exc:
                print(f"[itsm-sla-worker] cycle failed: {exc}")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="itsm-sla-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None


itsm_sla_worker = ITSMSLAWorker()
