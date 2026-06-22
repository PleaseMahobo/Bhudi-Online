import platform
import psutil
import socket

def collect():
    return {
        "agent_id": socket.gethostname(),
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent
    }