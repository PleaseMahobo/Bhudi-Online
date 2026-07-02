import socket
import psutil

def collect():
    return {
        "device_id": socket.gethostname(),
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "status": "online"
    }