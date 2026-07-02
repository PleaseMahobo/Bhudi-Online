from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True)
    status = Column(String)
    last_seen = Column(DateTime)
    ip = Column(String)