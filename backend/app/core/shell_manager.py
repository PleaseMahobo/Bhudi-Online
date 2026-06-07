from fastapi import WebSocket


class ShellManager:

    def __init__(self):
        self.agents = {}

    async def connect_agent(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.agents[device_id] = websocket

    def disconnect_agent(self, device_id: str):
        if device_id in self.agents:
            del self.agents[device_id]

    async def send_command(self, device_id: str, command: str):

        agent = self.agents.get(device_id)

        if not agent:
            return False

        await agent.send_json({
            "type": "command",
            "command": command
        })

        return True


shell_manager = ShellManager()