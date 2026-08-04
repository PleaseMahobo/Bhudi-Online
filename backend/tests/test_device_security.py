from __future__ import annotations

import os

from app.core.device_security import DeviceSecurity


def test_device_security_uses_local_fallback(monkeypatch) -> None:
    monkeypatch.setenv("BHUDI_DEVICE_SECRET", "test-secret")

    security = DeviceSecurity()
    device = security.create_device("device-123", name="agent")

    assert device["device_id"] == "device-123"
    assert security.verify_device("device-123", device["api_key"])
