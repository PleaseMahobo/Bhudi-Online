from fastapi import APIRouter

router = APIRouter()

@router.post("/ingest")
def ingest_agent(payload: dict):
    return {
        "status": "received",
        "device": payload
    }