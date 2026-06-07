from sqlalchemy import Column, String, DateTime, Text
from app.core.database import Base
from datetime import datetime
import uuid


class ShellSession(Base):
    __tablename__ = "shell_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, index=True)

    status = Column(String, default="active")  # active, closed

    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)