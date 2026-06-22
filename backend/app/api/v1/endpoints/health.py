# app/api/v1/endpoints/health.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def health():
    return {
        "status": "running",
        "service": "Bhudi RMM API"
    }