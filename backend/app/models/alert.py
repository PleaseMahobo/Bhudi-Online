from sqlalchemy import Column, Integer, String, DateTime
from app.database.base import Base
from datetime import datetime

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)