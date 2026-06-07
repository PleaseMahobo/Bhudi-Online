import asyncio
from app.websocket.event_stream import EventStream

class CommandDispatcher:
    def __init__(self, queue):
        self.queue = queue

    async def start(self):

        while True:
            cmd = self.queue.get_next()

            if cmd:
                await self.execute(cmd)

            await asyncio.sleep(1)

    async def execute(self, cmd):

        cmd.status = "running"

        # SIMULATED EXECUTION (replace with real agent call)
        await asyncio.sleep(2)

        cmd.status = "completed"
        cmd.result = {
            "output": f"Executed {cmd.command} on {cmd.agent_id}"
        }

        # PUSH BACK TO SOC DASHBOARD
        await EventStream.publish({
            "type": "command_result",
            "device_id": cmd.agent_id,
            "severity": "low",
            "payload": cmd.result
        })