import requests
from config import API_URL, AGENT_TOKEN

def send(payload):
    return requests.post(
        f"{API_URL}/agents/ingest",
        json=payload,
        headers={
            "Authorization": f"Bearer {AGENT_TOKEN}"
        },
        timeout=10
    )