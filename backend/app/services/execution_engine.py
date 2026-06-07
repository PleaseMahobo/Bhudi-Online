import asyncio
import uuid
from datetime import datetime

ALLOWED_COMMANDS = {
    "windows": ["ipconfig", "whoami", "hostname", "netstat -an"],
    "linux": ["ls", "whoami", "uname -a", "df -h"]
}

class ExecutionEngine:

    async def run_command(self, command: str, timeout: int = 30):
        """
        Safe subprocess execution (NOT full shell access)
        """

        cmd_parts = command.split()

        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "exit_code": process.returncode
            }

        except asyncio.TimeoutError:
            process.kill()
            return {
                "stdout": "",
                "stderr": "Execution timed out",
                "exit_code": -1
            }