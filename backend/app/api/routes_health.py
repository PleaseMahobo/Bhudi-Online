from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "running",
        "service": "Bhudi RMM API"
    }