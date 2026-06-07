from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket

    def disconnect(self, device_id: str):
        self.active_connections.pop(device_id, None)

    async def send(self, device_id: str, message: dict):
        ws = self.active_connections.get(device_id)
        if ws:
            await ws.send_json(message)

manager = ConnectionManager()