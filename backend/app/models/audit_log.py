from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    actor = Column(String)   # dashboard user / agent
    action = Column(String)   # execute_command, login, etc
    target = Column(String)   # device_id

    payload = Column(Text)

    timestamp = Column(DateTime, default=datetime.utcnow)