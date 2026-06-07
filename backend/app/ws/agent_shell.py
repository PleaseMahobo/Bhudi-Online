import asyncio
import subprocess
from fastapi import WebSocket

class AgentShell:
    def __init__(self):
        self.sessions = {}

    async def start_session(self, session_id: str, websocket: WebSocket):
        self.sessions[session_id] = websocket

    async def execute(self, session_id: str, command: str):
        websocket = self.sessions.get(session_id)
        if not websocket:
            return

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break

            await websocket.send_text(line.decode().strip())

shell = AgentShell()