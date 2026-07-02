from app.core.database import get_supabase

def upsert_device(device: dict):
    return get_supabase().table("devices").upsert(device).execute()


def get_devices():
    return get_supabase().table("devices").select("*").execute()


def update_device_status(device_id: str, status: dict):
    return (
        get_supabase()
        .table("devices")
        .update(status)
        .eq("device_id", device_id)
        .execute()
    )