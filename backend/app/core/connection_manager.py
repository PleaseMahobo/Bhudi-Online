from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        self.agents = {}
        self.dashboards = []

    async def connect_agent(
        self,
        device_id: str,
        websocket: WebSocket
    ):
        await websocket.accept()
        self.agents[device_id] = websocket

    def disconnect_agent(
        self,
        device_id: str
    ):
        if device_id in self.agents:
            del self.agents[device_id]

    async def connect_dashboard(
        self,
        websocket: WebSocket
    ):
        await websocket.accept()
        self.dashboards.append(websocket)

    def disconnect_dashboard(
        self,
        websocket: WebSocket
    ):
        if websocket in self.dashboards:
            self.dashboards.remove(websocket)

    async def send_to_agent(
        self,
        device_id: str,
        data: dict
    ):
        ws = self.agents.get(device_id)

        if ws:
            await ws.send_json(data)

    async def broadcast(
        self,
        data: dict
    ):
        dead = []

        for ws in self.dashboards:
            try:
                await ws.send_json(data)
            except:
                dead.append(ws)

        for ws in dead:
            self.disconnect_dashboard(ws)


manager = ConnectionManager()