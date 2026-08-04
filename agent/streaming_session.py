from __future__ import annotations

import asyncio
import json
import platform as platform_module
import threading
from typing import Any
from urllib.parse import urlparse

import websockets

from pty_engine import PTYSession


def session_websocket_url(server_url: str, session_id: str, agent_id: str) -> str:
    parsed = urlparse(server_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc or parsed.path
    return f"{scheme}://{netloc}/api/v1/remote-access/sessions/{session_id}/agent/{agent_id}"


class StreamingSessionCoordinator:
    def __init__(self) -> None:
        self._threads: dict[str, threading.Thread] = {}

    def start(self, *, server_url: str, agent_id: str, command: dict[str, Any]) -> dict[str, Any]:
        payload = command.get("payload") or {}
        session_id = payload.get("session_id")
        command_type = str(command.get("command_type") or "")
        if not session_id:
            return {"exit_code": 1, "stdout": "", "stderr": "session_id is required for interactive streaming"}
        if session_id in self._threads and self._threads[session_id].is_alive():
            return {
                "exit_code": 0,
                "stdout": f"session {session_id} already active",
                "stderr": "",
                "metadata": {"session_id": session_id, "streaming": True},
            }

        thread = threading.Thread(
            target=self._run,
            kwargs={
                "server_url": server_url,
                "agent_id": agent_id,
                "session_id": str(session_id),
                "command_type": command_type,
                "payload": payload,
            },
            daemon=True,
            name=f"RemoteSession-{session_id}",
        )
        self._threads[str(session_id)] = thread
        thread.start()
        return {
            "exit_code": 0,
            "stdout": f"started streaming session {session_id}",
            "stderr": "",
            "metadata": {
                "session_id": session_id,
                "streaming": True,
                "stream_path": f"/api/v1/remote-access/sessions/{session_id}/dashboard",
                "session_type": payload.get("session_type"),
            },
        }

    def _run(self, *, server_url: str, agent_id: str, session_id: str, command_type: str, payload: dict[str, Any]) -> None:
        asyncio.run(
            self._run_session(
                server_url=server_url,
                agent_id=agent_id,
                session_id=session_id,
                command_type=command_type,
                payload=payload,
            )
        )

    async def _run_session(self, *, server_url: str, agent_id: str, session_id: str, command_type: str, payload: dict[str, Any]) -> None:
        ws_url = session_websocket_url(server_url, session_id, agent_id)
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as websocket:
            if command_type == "remote.terminal.start":
                await self._run_terminal_session(websocket, session_id, payload)
                return
            await self._run_desktop_session(websocket, session_id, payload)

    async def _run_terminal_session(self, websocket: Any, session_id: str, payload: dict[str, Any]) -> None:
        shell_name = str(payload.get("shell") or "")
        family = platform_module.system().lower()
        shell_command = self._shell_for_platform(shell_name, family)
        pty = PTYSession(
            session_id,
            shell_command=shell_command,
            cwd=payload.get("working_directory"),
            environment=payload.get("environment"),
        )
        pty.start()

        await websocket.send(json.dumps({
            "type": "ready",
            "session_id": session_id,
            "shell": shell_command,
            "platform": family,
        }))

        receiver = asyncio.create_task(self._terminal_receiver(websocket, pty, session_id))
        try:
            while pty.alive:
                output = "".join(pty.read_all())
                if output:
                    await websocket.send(json.dumps({"type": "output", "session_id": session_id, "data": output}))
                await asyncio.sleep(0.1)
                if receiver.done():
                    break
        finally:
            pty.stop()
            if not receiver.done():
                receiver.cancel()
            await websocket.send(json.dumps({"type": "session_closed", "session_id": session_id, "reason": "terminal_stopped"}))

    async def _terminal_receiver(self, websocket: Any, pty: PTYSession, session_id: str) -> None:
        while True:
            message = json.loads(await websocket.recv())
            msg_type = str(message.get("type") or "")
            if msg_type == "session_attached":
                continue
            if msg_type == "dashboard_message":
                payload = message.get("payload") or {}
                nested_type = str(payload.get("type") or "")
                if nested_type == "input":
                    pty.write(str(payload.get("data") or ""))
                elif nested_type == "command":
                    pty.send(str(payload.get("command") or ""))
                elif nested_type == "resize":
                    await websocket.send(json.dumps({"type": "resize_ack", "session_id": session_id, "rows": payload.get("rows"), "cols": payload.get("cols")}))
                elif nested_type == "close":
                    pty.stop()
                    return

    async def _run_desktop_session(self, websocket: Any, session_id: str, payload: dict[str, Any]) -> None:
        await websocket.send(json.dumps({
            "type": "desktop_ready",
            "session_id": session_id,
            "platform": platform_module.system().lower(),
            "display_protocol": payload.get("display_protocol"),
            "session_mode": payload.get("session_mode"),
        }))
        await websocket.send(json.dumps({
            "type": "frame",
            "session_id": session_id,
            "data": "interactive desktop transport ready",
        }))
        while True:
            message = json.loads(await websocket.recv())
            msg_type = str(message.get("type") or "")
            if msg_type == "session_attached":
                continue
            if msg_type == "dashboard_message":
                payload = message.get("payload") or {}
                nested_type = str(payload.get("type") or "")
                if nested_type == "close":
                    await websocket.send(json.dumps({"type": "session_closed", "session_id": session_id, "reason": "closed_by_operator"}))
                    return
                await websocket.send(json.dumps({
                    "type": "desktop_event_ack",
                    "session_id": session_id,
                    "event": nested_type,
                    "payload": payload,
                }))

    def _shell_for_platform(self, shell_name: str, family: str) -> str:
        requested = shell_name.lower()
        if requested == "powershell":
            return "powershell.exe"
        if requested == "cmd":
            return "cmd.exe"
        if requested:
            return requested if family == "windows" else f"/bin/{requested}"
        if family.startswith("win"):
            return "powershell.exe"
        if family.startswith("darwin"):
            return "/bin/zsh"
        return "/bin/bash"


streaming_session_coordinator = StreamingSessionCoordinator()