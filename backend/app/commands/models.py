from datetime import datetime, timezone
from uuid import uuid4

class Command:
    def __init__(self, agent_id: str, command: str, payload: dict = None):

        self.id = str(uuid4())
        self.agent_id = agent_id
        self.command = command
        self.payload = payload or {}

        self.status = "queued"
        self.created_at = datetime.now(timezone.utc)
        self.result = None