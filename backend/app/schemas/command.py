try:
    from pydantic import BaseModel
except Exception:
    # lightweight fallback for editors/static analysis when pydantic isn't available
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self):
            return self.__dict__.copy()

from datetime import datetime
from typing import Optional

class CommandCreate(BaseModel):
    device_id: str
    command: str

class CommandRequest(CommandCreate):
    pass

class CommandResult(BaseModel):
    device_id: Optional[str] = None
    command: Optional[str] = None
    result: Optional[str] = None
    created_at: Optional[datetime] = None