import requests
from config import API_URL

def send(payload):
    return requests.post(
        f"{API_URL}/agents/heartbeat",
        json=payload,
        timeout=10
    )