# backend/app/core/command_repository.py

from app.core.supabase_client import supabase
from datetime import datetime


class CommandRepository:

    def create_command(self, device_id: str, command: str):
        return supabase.table("commands").insert({
            "device_id": device_id,
            "command": command,
            "status": "pending"
        }).execute()

    def get_pending_commands(self, device_id: str):
        return supabase.table("commands") \
            .select("*") \
            .eq("device_id", device_id) \
            .eq("status", "pending") \
            .execute()

    def mark_executed(self, command_id: str, result: str):
        return supabase.table("commands").update({
            "status": "completed",
            "result": result,
            "executed_at": datetime.utcnow().isoformat()
        }).eq("id", command_id).execute()