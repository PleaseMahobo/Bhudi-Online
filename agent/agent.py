import asyncio
import websockets
import subprocess
import json

DEVICE_ID = 1
URL = f"ws://localhost:8000/ws/{DEVICE_ID}"


async def run():

    async with websockets.connect(URL) as ws:

        while True:

            msg = await ws.recv()
            data = json.loads(msg)

            if data["type"] == "command":

                cmd = data["command"]

                try:
                    result = subprocess.check_output(
                        cmd,
                        shell=True,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                except Exception as e:
                    result = str(e)

                await ws.send(json.dumps({
                    "type": "result",
                    "command_id": data["command_id"],
                    "result": result
                }))


asyncio.run(run())