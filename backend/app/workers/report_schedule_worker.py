"""Background worker: process due report schedules (including daily device health)."""
from __future__ import annotations

import os
import threading
import time


class ReportScheduleWorker:
    def __init__(self) -> None:
        self.interval = max(60, int(os.getenv("BHUDI_REPORT_SCHEDULE_INTERVAL_SECONDS", "300")))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> int:
        from app.database.session import SessionLocal
        from app.services.reporting_service import ReportingService

        db = SessionLocal()
        try:
            runs = ReportingService(db).process_due_schedules(limit=20)
            return len(runs)
        finally:
            db.close()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                n = self.run_once()
                if n:
                    print(f"[report-schedule-worker] processed {n} due schedule(s)")
            except Exception as exc:
                print(f"[report-schedule-worker] cycle failed: {exc}")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="report-schedule-worker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None


report_schedule_worker = ReportScheduleWorker()
