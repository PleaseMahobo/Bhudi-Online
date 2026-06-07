from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime
from app.core.database import Base


class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(Integer, ForeignKey("devices.id"), index=True)

    command = Column(String, nullable=False)   # e.g. "ipconfig"
    status = Column(String, default="pending") # pending | running | done | failed

    result = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)