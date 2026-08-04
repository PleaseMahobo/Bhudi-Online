from datetime import datetime, timezone
import uuid

command_queue = {}

def queue_command(device_id: str, command: str):
    command_id = str(uuid.uuid4())

    command_queue[command_id] = {
        "command_id": command_id,
        "device_id": device_id,
        "command": command,
        "status": "pending",
        "created": datetime.now(timezone.utc).isoformat(),
        "executed": None,
        "result": None
    }

    return command_queue[command_id]

def get_pending_commands(device_id: str):
    return [
        cmd
        for cmd in command_queue.values()
        if cmd["device_id"] == device_id
        and cmd["status"] == "pending"
    ]

def complete_command(command_id: str, result: str):
    if command_id in command_queue:
        command_queue[command_id]["status"] = "completed"
        command_queue[command_id]["executed"] = datetime.now(timezone.utc).isoformat()
        command_queue[command_id]["result"] = result

def failed_command(command_id: str, error: str):
    if command_id in command_queue:
        command_queue[command_id]["status"] = "failed"
        command_queue[command_id]["executed"] = datetime.now(timezone.utc).isoformat()
        command_queue[command_id]["result"] = error

def get_all_commands():
    return list(command_queue.values())