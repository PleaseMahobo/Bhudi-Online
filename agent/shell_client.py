import asyncio
import websockets
import json
from pty_engine import PTYSession

SERVER_WS = "ws://127.0.0.1:8000/ws/agent/shell"


sessions = {}


async def run():
    async with websockets.connect(SERVER_WS) as ws:

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            session_id = data["session_id"]
            command = data.get("command")

            # CREATE SESSION IF NEW
            if session_id not in sessions:
                session = PTYSession(session_id)
                session.start()
                sessions[session_id] = session

            session = sessions[session_id]

            # SEND COMMAND TO PTY
            if command:
                session.send(command)

            # READ OUTPUT
            output = session.read_all()

            if output:
                await ws.send(json.dumps({
                    "session_id": session_id,
                    "output": "".join(output)
                }))


asyncio.run(run())