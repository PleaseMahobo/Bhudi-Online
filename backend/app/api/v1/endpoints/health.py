from fastapi import APIRouter

router = APIRouter()


@router.get("")
def health():
    return {"status": "running"}


@router.get("/db")
def health_db():
    """Database connectivity diagnostic (no credentials)."""
    try:
        from app.database.session import db_health

        result = db_health()
        result["status"] = "ok" if result.get("ok") else "error"
        return result
    except Exception as exc:
        return {
            "status": "error",
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
