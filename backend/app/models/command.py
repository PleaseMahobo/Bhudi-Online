from pydantic import BaseModel

class CommandRequest(BaseModel):
    device_id: int
    command: str

