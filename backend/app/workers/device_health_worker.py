"""Background worker: missed-heartbeat tracking + auto status + health scores."""
from __future__ import annotations

import os
import threading
import time

from app.database.session import SessionLocal
from app.services.device_health_service import DeviceHealthService


class DeviceHealthWorker:
    def __init__(self) -> None:
        self.interval = max(10, int(os.getenv("BHUDI_HEALTH_WORKER_INTERVAL_SECONDS", "30")))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> dict:
        db = SessionLocal()
        try:
            return DeviceHealthService(db).process_stale_endpoints()
        finally:
            db.close()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                stats = self.run_once()
                updated = stats.get("agents_updated", 0) + stats.get("devices_updated", 0)
                if updated:
                    print(
                        f"[device-health-worker] agents={stats.get('agents_updated', 0)} "
                        f"devices={stats.get('devices_updated', 0)} "
                        f"offline={stats.get('offline', 0)} overdue={stats.get('overdue', 0)}"
                    )
            except Exception as exc:
                print(f"[device-health-worker] cycle failed: {exc}")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="device-health-worker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None


device_health_worker = DeviceHealthWorker()
