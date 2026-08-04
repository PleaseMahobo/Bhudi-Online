# backend/app/core/device_security.py

import os
import secrets
import hashlib

from app.core.supabase_client import supabase


class DeviceSecurity:

    def _local_secret(self) -> str:
        return os.getenv("BHUDI_DEVICE_SECRET", "local-device-secret")

    def _derive_api_key(self, device_id: str, name: str) -> str:
        payload = f"{device_id}:{name}:{self._local_secret()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def create_device(self, device_id: str, name: str = "agent"):
        api_key = self._derive_api_key(device_id, name)

        if supabase is not None:
            supabase.table("devices").insert({
                "device_id": device_id,
                "api_key": api_key,
                "name": name,
                "status": "offline"
            }).execute()

        return {
            "device_id": device_id,
            "api_key": api_key
        }

    def verify_device(self, device_id: str, api_key: str):
        if supabase is None:
            expected = self._derive_api_key(device_id, "agent")
            return api_key == expected

        result = supabase.table("devices") \
            .select("*") \
            .eq("device_id", device_id) \
            .eq("api_key", api_key) \
            .execute()

        return len(result.data) > 0