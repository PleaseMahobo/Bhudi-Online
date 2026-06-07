from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.shell_service import create_session

router = APIRouter()


@router.post("/shell/start")
def start_shell(device_id: str, db: Session = Depends(get_db)):
    session = create_session(db, device_id)
    return {"session_id": session.id}