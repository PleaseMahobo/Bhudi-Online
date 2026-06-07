# backend/app/core/device_security.py

import secrets
from app.core.supabase_client import supabase


class DeviceSecurity:

    def create_device(self, device_id: str, name: str = "agent"):
        api_key = secrets.token_hex(32)

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
        result = supabase.table("devices") \
            .select("*") \
            .eq("device_id", device_id) \
            .eq("api_key", api_key) \
            .execute()

        return len(result.data) > 0