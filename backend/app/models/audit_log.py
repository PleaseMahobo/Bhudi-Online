from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    actor = Column(String)   # dashboard user / agent
    action = Column(String)   # execute_command, login, etc
    target = Column(String)   # device_id

    payload = Column(Text)

    timestamp = Column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc),
)