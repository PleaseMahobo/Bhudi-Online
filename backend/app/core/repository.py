# backend/app/core/repository.py

from app.core.supabase_client import supabase
from datetime import datetime


class DeviceRepository:

    def upsert_heartbeat(self, device_id: str, status: str):
        """
        Insert or update device heartbeat
        """
        return supabase.table("devices").upsert({
            "device_id": device_id,
            "status": status,
            "last_seen": datetime.utcnow().isoformat()
        }).execute()

    def list_devices(self):
        return supabase.table("devices").select("*").execute()

    def mark_offline(self, device_id: str):
        return supabase.table("devices").update({
            "status": "offline"
        }).eq("device_id", device_id).execute()