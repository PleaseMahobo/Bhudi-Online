from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.core.access_tiers import require_mfa_for_actions
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.remote_access_service import RemoteAccessService
from app.services.remote_session_manager import remote_session_manager

router = APIRouter(prefix="/remote-access", tags=["remote-access"])


class RemoteAccessQueuedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    command_id: UUID
    agent_id: UUID
    operation: str
    command_type: str
    status: str
    priority: int
    timeout_seconds: int
    requires_reboot: bool
    payload: dict[str, Any]
    session_id: str | None = None
    session_status: str | None = None
    stream_path: str | None = None
    result: dict[str, Any] | None = None
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None


class RemoteDesktopRequest(BaseModel):
    agent_id: UUID
    session_mode: Literal["view", "control"] = "control"
    display_protocol: Literal["native", "rdp", "vnc"] = "native"
    consent_required: bool = False


class RemoteTerminalRequest(BaseModel):
    agent_id: UUID
    shell: Literal["powershell", "cmd", "bash", "zsh", "sh"]
    working_directory: str | None = None
    environment: dict[str, str] | None = None
    interactive: bool = True


class FileBrowserRequest(BaseModel):
    agent_id: UUID
    operation: Literal["list", "download", "upload", "delete", "mkdir", "stat"]
    path: str = Field(min_length=1)
    destination_path: str | None = None
    overwrite: bool = False
    recursive: bool = False
    content_b64: str | None = None

    @model_validator(mode="after")
    def validate_file_operation(self) -> "FileBrowserRequest":
        if self.operation == "upload" and not self.content_b64:
            raise ValueError("content_b64 is required for upload operations")
        if self.operation == "download" and not self.destination_path:
            raise ValueError("destination_path is required for download operations")
        return self


class RegistryEditorRequest(BaseModel):
    agent_id: UUID
    operation: Literal["get", "set", "delete", "list"]
    hive: Literal["HKLM", "HKCU", "HKCR", "HKU", "HKCC"]
    key_path: str = Field(min_length=1)
    value_name: str | None = None
    value_type: Literal["string", "expand_string", "dword", "qword", "binary", "multi_string"] | None = None
    value_data: Any | None = None

    @model_validator(mode="after")
    def validate_registry_operation(self) -> "RegistryEditorRequest":
        if self.operation == "set":
            if self.value_name is None or self.value_type is None:
                raise ValueError("value_name and value_type are required for set operations")
        return self


class TaskManagerRequest(BaseModel):
    agent_id: UUID
    operation: Literal[
        "list_processes",
        "list_services",
        "terminate_process",
        "start_service",
        "stop_service",
        "restart_service",
    ]
    process_id: int | None = None
    image_name: str | None = None
    service_name: str | None = None

    @model_validator(mode="after")
    def validate_task_manager_operation(self) -> "TaskManagerRequest":
        if self.operation == "terminate_process" and self.process_id is None and self.image_name is None:
            raise ValueError("process_id or image_name is required for terminate_process")
        if self.operation in {"start_service", "stop_service", "restart_service"} and self.service_name is None:
            raise ValueError("service_name is required for service operations")
        return self


class ShellExecutionRequest(BaseModel):
    agent_id: UUID
    command: str = Field(min_length=1)
    arguments: list[str] | None = None
    working_directory: str | None = None
    timeout_seconds: int = Field(default=300, ge=5, le=7200)
    run_as_system: bool = True


class EventViewerRequest(BaseModel):
    agent_id: UUID
    log_name: str = Field(min_length=1)
    provider: str | None = None
    levels: list[Literal["critical", "error", "warning", "information", "verbose"]] | None = None
    event_ids: list[int] | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    since_minutes: int | None = Field(default=None, ge=1, le=10080)


class WakeOnLanRequest(BaseModel):
    agent_id: UUID
    mac_address: str = Field(min_length=12)
    broadcast_address: str = "255.255.255.255"
    port: int = Field(default=9, ge=1, le=65535)


class RebootRequest(BaseModel):
    agent_id: UUID
    force: bool = True
    delay_seconds: int = Field(default=0, ge=0, le=3600)
    message: str | None = None


class SafeModeRebootRequest(BaseModel):
    agent_id: UUID
    force: bool = True
    delay_seconds: int = Field(default=0, ge=0, le=3600)
    with_networking: bool = True
    message: str | None = None


class RemoteSessionResponse(BaseModel):
    session_id: str
    agent_id: str
    session_type: str
    command_id: str | None = None
    status: str
    metadata: dict[str, Any]
    created_at: str
    agent_connected: bool
    dashboard_count: int
    transcript_length: int


def _service(db: Session = Depends(get_db)) -> RemoteAccessService:
    return RemoteAccessService(db)


def _session_response(session: Any) -> RemoteSessionResponse:
    snapshot = session.snapshot()
    return RemoteSessionResponse(**snapshot)


def _queued_response(command: Any, operation: str, service: RemoteAccessService | None = None) -> RemoteAccessQueuedResponse:
    payload = command.payload if isinstance(command.payload, dict) else {}
    session_id = payload.get("session_id") if isinstance(payload, dict) else None
    session_status = None
    if session_id and service is not None:
        session = service.get_session(session_id)
        session_status = session.status if session is not None else None
    return RemoteAccessQueuedResponse(
        command_id=command.id,
        agent_id=command.agent_id,
        operation=operation,
        command_type=command.command_type,
        status=command.status,
        priority=command.priority,
        timeout_seconds=command.timeout_seconds,
        requires_reboot=command.requires_reboot,
        payload=payload,
        session_id=session_id,
        session_status=session_status,
        stream_path=f"/api/v1/remote-access/sessions/{session_id}/dashboard" if session_id else None,
        result=command.result,
        stdout=command.stdout,
        stderr=command.stderr,
        exit_code=command.exit_code,
    )


@router.get("/capabilities", response_model=list[dict[str, Any]])
def list_capabilities(
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return service.list_capabilities()


@router.post("/desktop", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def open_remote_desktop(
    payload: RemoteDesktopRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    session = service.create_interactive_session(
        agent_id=payload.agent_id,
        session_type="desktop",
        metadata=payload.model_dump(exclude={"agent_id"}),
    )
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="remote_desktop",
        payload={
            **payload.model_dump(exclude={"agent_id"}),
            "session_id": session.session_id,
            "session_type": "desktop",
        },
        priority=90,
        timeout_seconds=1800,
    )
    service.attach_session_to_command(session.session_id, command.id)
    return _queued_response(command, "remote_desktop", service)


@router.post("/terminal", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def open_remote_terminal(
    payload: RemoteTerminalRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    session = None
    request_payload = payload.model_dump(exclude={"agent_id"}, exclude_none=True)
    if payload.interactive:
        session = service.create_interactive_session(
            agent_id=payload.agent_id,
            session_type="terminal",
            metadata=request_payload,
        )
        request_payload = {
            **request_payload,
            "session_id": session.session_id,
            "session_type": "terminal",
        }
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="remote_terminal",
        payload=request_payload,
        priority=80,
        timeout_seconds=1800,
    )
    if session is not None:
        service.attach_session_to_command(session.session_id, command.id)
    return _queued_response(command, "remote_terminal", service)


@router.post("/file-browser", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def queue_file_browser_operation(
    payload: FileBrowserRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="file_browser",
        payload=payload.model_dump(exclude={"agent_id"}, exclude_none=True),
        priority=70,
        timeout_seconds=900,
    )
    return _queued_response(command, "file_browser", service)


@router.post("/registry", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def queue_registry_operation(
    payload: RegistryEditorRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="registry_editor",
        payload=payload.model_dump(exclude={"agent_id"}, exclude_none=True),
        priority=75,
        timeout_seconds=600,
    )
    return _queued_response(command, "registry_editor", service)


@router.post("/task-manager", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def queue_task_manager_operation(
    payload: TaskManagerRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="task_manager",
        payload=payload.model_dump(exclude={"agent_id"}, exclude_none=True),
        priority=70,
        timeout_seconds=600,
    )
    return _queued_response(command, "task_manager", service)


@router.post("/powershell", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def run_remote_powershell(
    payload: ShellExecutionRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="remote_powershell",
        payload={**payload.model_dump(exclude={"agent_id"}), "shell": "powershell"},
        priority=80,
        timeout_seconds=payload.timeout_seconds,
    )
    return _queued_response(command, "remote_powershell", service)


@router.post("/cmd", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def run_remote_cmd(
    payload: ShellExecutionRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="remote_cmd",
        payload={**payload.model_dump(exclude={"agent_id"}), "shell": "cmd"},
        priority=80,
        timeout_seconds=payload.timeout_seconds,
    )
    return _queued_response(command, "remote_cmd", service)


@router.post("/event-viewer", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def queue_event_viewer_query(
    payload: EventViewerRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="remote_event_viewer",
        payload=payload.model_dump(exclude={"agent_id"}, exclude_none=True),
        priority=60,
        timeout_seconds=600,
    )
    return _queued_response(command, "remote_event_viewer", service)


@router.post("/wake-on-lan", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def queue_wake_on_lan(
    payload: WakeOnLanRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="wake_on_lan",
        payload=payload.model_dump(exclude={"agent_id"}),
        priority=100,
        timeout_seconds=120,
    )
    return _queued_response(command, "wake_on_lan", service)


@router.post("/reboot", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def queue_reboot(
    payload: RebootRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="remote_reboot",
        payload=payload.model_dump(exclude={"agent_id"}, exclude_none=True),
        priority=100,
        timeout_seconds=600,
        requires_reboot=True,
    )
    return _queued_response(command, "remote_reboot", service)


@router.post("/safe-mode-reboot", response_model=RemoteAccessQueuedResponse, status_code=status.HTTP_201_CREATED)
def queue_safe_mode_reboot(
    payload: SafeModeRebootRequest,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteAccessQueuedResponse:
    command = service.queue_operation(
        agent_id=payload.agent_id,
        operation="safe_mode_reboot",
        payload=payload.model_dump(exclude={"agent_id"}, exclude_none=True),
        priority=100,
        timeout_seconds=600,
        requires_reboot=True,
    )
    return _queued_response(command, "safe_mode_reboot", service)


@router.get("/operations/{command_id}", response_model=RemoteAccessQueuedResponse)
def get_remote_access_operation(
    command_id: UUID,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(get_current_user),
) -> RemoteAccessQueuedResponse:
    command = service.get_operation(command_id)
    if command is None or not service.is_remote_access_command(command):
        raise HTTPException(status_code=404, detail="remote access operation not found")

    operation = command.payload.get("operation") if isinstance(command.payload, dict) else None
    return _queued_response(command, operation or command.command_type, service)


@router.get("/sessions/{session_id}", response_model=RemoteSessionResponse)
def get_remote_session(
    session_id: str,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(get_current_user),
) -> RemoteSessionResponse:
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="remote session not found")
    return _session_response(session)


@router.post("/sessions/{session_id}/close", response_model=RemoteSessionResponse)
async def close_remote_session(
    session_id: str,
    service: RemoteAccessService = Depends(_service),
    _user: User = Depends(require_mfa_for_actions),
) -> RemoteSessionResponse:
    session = await remote_session_manager.close_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="remote session not found")
    return _session_response(session)


@router.websocket("/sessions/{session_id}/dashboard")
async def dashboard_session_stream(websocket: WebSocket, session_id: str) -> None:
    session = await remote_session_manager.connect_dashboard(session_id, websocket)
    if session is None:
        return
    try:
        while True:
            message = await websocket.receive_json()
            await remote_session_manager.relay_dashboard_message(session_id, message)
    except WebSocketDisconnect:
        await remote_session_manager.disconnect_dashboard(session_id, websocket)


@router.websocket("/sessions/{session_id}/agent/{agent_id}")
async def agent_session_stream(websocket: WebSocket, session_id: str, agent_id: str) -> None:
    session = await remote_session_manager.connect_agent(session_id, agent_id, websocket)
    if session is None:
        return
    try:
        while True:
            message = await websocket.receive_json()
            await remote_session_manager.relay_agent_message(session_id, message)
    except WebSocketDisconnect:
        await remote_session_manager.disconnect_agent(session_id, websocket)
