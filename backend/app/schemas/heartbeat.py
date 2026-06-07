from pydantic import BaseModel
from datetime import datetime


class Heartbeat(BaseModel):
    device_id: str
    hostname: str
    timestamp: datetime
    