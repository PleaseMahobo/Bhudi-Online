from fastapi import APIRouter

router = APIRouter()

@router.post("/commands")
def send_command(payload: dict):
    return {
        "status": "received",
        "payload": payload
    }