from datetime import datetime
import json

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.core.database import SessionLocal
from app.models.shell_session import ShellSession
from app.ws.agent_shell import agent_socket

router = APIRouter()

active_connections = {}


@router.websocket("/ws/shell/{session_id}")
async def shell_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()

    db = SessionLocal()

    session = db.query(ShellSession).filter(
        ShellSession.id == session_id
    ).first()

    if not session:
        await websocket.close()
        return

    active_connections[session_id] = websocket

    try:
        while True:
            from app.ws.agent_shell import agent_socket

            data = await websocket.receive_text()

            if agent_socket:
                await agent_socket.send_text(
                    json.dumps(
                        {
                            "session_id": session_id,
                            "command": data,
                        }
                    )
                )

            # In the production RMM this will be forwarded
            # through the command queue to the agent.
            print(f"[SHELL INPUT] {session_id}: {data}")

            # Temporary echo until live shell streaming is implemented.
            await websocket.send_text(f"executed: {data}")

            session.last_activity = datetime.utcnow()
            db.commit()

    except WebSocketDisconnect:
        active_connections.pop(session_id, None)

        session.status = "closed"
        db.commit()

    finally:
        db.close()


