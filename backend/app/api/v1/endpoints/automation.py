from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.action import Action
from app.models.automation_log import AutomationLog
from app.models.response_action import ResponseAction
from app.models.script import Script
from app.models.script_task import ScriptTask

router = APIRouter(prefix="/automation", tags=["automation"])


class AutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    message: str
    data: dict[str, Any]


class AutomationRunRequest(BaseModel):
    device_id: UUID
    script_name: str
    shell: str = "powershell"
    content: str
    parameters: dict[str, Any] | None = None
    incident_id: UUID | None = None
    response_action: str | None = None


class AutomationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID | None = None
    action: str | None = None
    result: str | None = None
    created_at: Any | None = None


def _get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


@router.post("/run", response_model=AutomationResponse)
def run_automation(payload: AutomationRunRequest, db: Session = Depends(_get_db_session)) -> AutomationResponse:
    device_id = str(payload.device_id)
    tenant_id = str(payload.device_id)

    script = Script(
        name=payload.script_name,
        description="runtime automation script",
        shell=payload.shell,
        content=payload.content,
    )
    db.add(script)
    db.flush()

    task_parameters = dict(payload.parameters or {})
    if payload.incident_id is not None:
        task_parameters["incident_id"] = str(payload.incident_id)
        task_parameters["response_action"] = payload.response_action or "automation.run"

    task = ScriptTask(
        script_id=script.id,
        device_id=device_id,
        tenant_id=tenant_id,
        status="queued",
        parameters=task_parameters,
    )
    db.add(task)
    db.flush()

    action = Action(
        device_id=device_id,
        tenant_id=tenant_id,
        type="automation.run",
        payload={"script_id": str(script.id), "task_id": str(task.id)},
        status="queued",
        result="queued",
    )
    db.add(action)

    response_action = None
    if payload.incident_id is not None:
        response_action = ResponseAction(
            incident_id=str(payload.incident_id),
            device_id=device_id,
            tenant_id=tenant_id,
            action=payload.response_action or "automation.run",
            status="queued",
            initiated_by="automation-engine",
        )
        db.add(response_action)

    log = AutomationLog(
        action="automation.run",
        result="queued",
    )
    db.add(log)
    db.commit()
    db.refresh(script)
    db.refresh(task)
    db.refresh(action)
    db.refresh(log)

    data = {"script_id": str(script.id), "task_id": str(task.id), "action_id": str(action.id)}
    if response_action is not None:
        db.refresh(response_action)
        data["response_action_id"] = str(response_action.id)

    return AutomationResponse(
        status="queued",
        message="Automation task accepted",
        data=data,
    )


@router.get("/logs", response_model=list[AutomationLogResponse])
def list_automation_logs(db: Session = Depends(_get_db_session)) -> list[AutomationLogResponse]:
    logs = db.query(AutomationLog).order_by(AutomationLog.created_at.desc()).all()
    return [AutomationLogResponse.model_validate(log) for log in logs]


@router.get("/tasks/{task_id}", response_model=AutomationResponse)
def get_task_status(task_id: UUID, db: Session = Depends(_get_db_session)) -> AutomationResponse:
    task = db.get(ScriptTask, str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return AutomationResponse(
        status=task.status,
        message="task status retrieved",
        data={"task_id": str(task.id), "status": task.status, "exit_code": task.exit_code},
    )


@router.post("/tasks/{task_id}/state", response_model=AutomationResponse)
def update_task_state(task_id: UUID, payload: dict[str, Any], db: Session = Depends(_get_db_session)) -> AutomationResponse:
    task = db.get(ScriptTask, str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    task.status = payload.get("status", task.status)
    task.exit_code = payload.get("exit_code")
    task.output = payload.get("output")
    task.error_output = payload.get("error_output")
    if payload.get("completed"):
        task.completed_at = payload.get("completed_at")

    response_action = None
    task_parameters = task.parameters or {}
    if isinstance(task_parameters, dict):
        incident_id = task_parameters.get("incident_id")
        if incident_id:
            response_action = (
                db.query(ResponseAction)
                .filter(
                    ResponseAction.incident_id == str(incident_id),
                    ResponseAction.device_id == str(task.device_id),
                )
                .order_by(ResponseAction.created_at.desc())
                .first()
            )

    if response_action is not None:
        response_action.status = task.status
        response_action.output = task.output or response_action.output
        if payload.get("completed"):
            response_action.completed_at = payload.get("completed_at") or datetime.utcnow()
        db.add(response_action)

    db.add(task)
    db.commit()
    db.refresh(task)

    response_data = {"task_id": str(task.id), "status": task.status}
    if response_action is not None:
        response_data["response_action_status"] = response_action.status

    return AutomationResponse(
        status=task.status,
        message="task state updated",
        data=response_data,
    )
