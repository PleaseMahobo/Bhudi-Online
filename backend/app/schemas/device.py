from pydantic import BaseModel
from typing import Optional, Dict


class DeviceRegister(BaseModel):
    device_id: str
    metadata: Optional[Dict] = None


class HeartbeatIn(BaseModel):
    device_id: str
    timestamp: str
    status: str