from sqlalchemy.orm import Session
from app.models.shell_session import ShellSession
from datetime import datetime
import uuid


def create_session(db: Session, device_id: str):
    session = ShellSession(
        id=str(uuid.uuid4()),
        device_id=device_id,
        status="active"
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def close_session(db: Session, session_id: str):
    session = db.query(ShellSession).filter(
        ShellSession.id == session_id
    ).first()

    if session:
        session.status = "closed"
        db.commit()

    return session