from fastapi import WebSocket, APIRouter
import json

router = APIRouter()

agent_socket = None


@router.websocket("/ws/agent/shell")
async def agent_shell(websocket: WebSocket):
    global agent_socket
    await websocket.accept()
    agent_socket = websocket

    while True:
        data = await websocket.receive_text()

        # This is output from agent
        print("[AGENT OUTPUT]", data)