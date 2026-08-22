from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.action import Action
from app.models.automation_log import AutomationLog
from app.models.response_action import ResponseAction
from app.models.script import Script
from app.models.script_task import ScriptTask
from app.services.script_execution import (
    ScriptExecutionError,
    classify_outcome,
    normalize_task_status,
    truncate_output,
    utcnow,
    validate_script_content,
    validate_shell,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])


def _try_get_remediation_run_model():
    """Optional link to alert remediation (present after that feature lands)."""
    try:
        from app.models.remediation_run import RemediationRun

        return RemediationRun
    except Exception:
        return None


class AutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    message: str
    data: dict[str, Any]


class AutomationRunRequest(BaseModel):
    device_id: UUID
    script_name: str = Field(..., min_length=1, max_length=255)
    shell: str = "powershell"
    content: str = Field(..., min_length=1)
    parameters: dict[str, Any] | None = None
    incident_id: UUID | None = None
    response_action: str | None = None

    @field_validator("shell")
    @classmethod
    def _shell(cls, v: str) -> str:
        return validate_shell(v)

    @field_validator("content")
    @classmethod
    def _content(cls, v: str) -> str:
        return validate_script_content(v)


class TaskStateUpdate(BaseModel):
    """Agent / worker callback when a script task progresses or finishes."""

    status: str | None = None
    exit_code: int | None = None
    output: str | None = None
    error_output: str | None = None
    completed: bool = False
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


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
def run_automation(
    payload: AutomationRunRequest, db: Session = Depends(_get_db_session)
) -> AutomationResponse:
    try:
        shell = validate_shell(payload.shell)
        content = validate_script_content(payload.content)
    except ScriptExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    device_id = str(payload.device_id)
    tenant_id = str(payload.device_id)

    try:
        script = Script(
            name=payload.script_name.strip(),
            description="runtime automation script",
            shell=shell,
            content=content,
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

        data: dict[str, Any] = {
            "script_id": str(script.id),
            "task_id": str(task.id),
            "action_id": str(action.id),
        }
        if response_action is not None:
            db.refresh(response_action)
            data["response_action_id"] = str(response_action.id)

        return AutomationResponse(
            status="queued",
            message="Automation task accepted",
            data=data,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to queue automation script")
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue automation task",
        )


@router.get("/logs", response_model=list[AutomationLogResponse])
def list_automation_logs(db: Session = Depends(_get_db_session)) -> list[AutomationLogResponse]:
    logs = (
        db.query(AutomationLog)
        .order_by(AutomationLog.created_at.desc())
        .limit(200)
        .all()
    )
    return [AutomationLogResponse.model_validate(log) for log in logs]


@router.get("/tasks/{task_id}", response_model=AutomationResponse)
def get_task_status(task_id: UUID, db: Session = Depends(_get_db_session)) -> AutomationResponse:
    task = db.get(ScriptTask, str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    outcome = classify_outcome(
        status=task.status or "unknown",
        exit_code=task.exit_code,
        error_output=task.error_output,
    )
    return AutomationResponse(
        status=task.status,
        message="task status retrieved",
        data={
            "task_id": str(task.id),
            "status": task.status,
            "exit_code": task.exit_code,
            "outcome": outcome,
            "has_error_output": bool(task.error_output),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
    )


@router.post("/tasks/{task_id}/state", response_model=AutomationResponse)
def update_task_state(
    task_id: UUID,
    payload: TaskStateUpdate,
    db: Session = Depends(_get_db_session),
) -> AutomationResponse:
    task = db.get(ScriptTask, str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    try:
        exit_code = payload.exit_code
        error_output = truncate_output(payload.error_output or payload.error_message)
        output = truncate_output(payload.output)

        completed = bool(payload.completed) or bool(payload.error_code)
        if payload.error_code and not payload.status:
            requested = "failed"
            completed = True
        else:
            requested = payload.status

        new_status = normalize_task_status(
            requested_status=requested,
            exit_code=exit_code,
            error_output=error_output,
            completed=completed,
        )

        task.status = new_status
        if exit_code is not None:
            task.exit_code = exit_code
        if output is not None:
            task.output = output
        if error_output is not None:
            task.error_output = error_output

        terminal = new_status in {"success", "failed", "timed_out", "cancelled"}
        if terminal or completed:
            task.completed_at = payload.completed_at or task.completed_at or utcnow()
            if not task.started_at:
                try:
                    task.started_at = task.completed_at
                except Exception:
                    pass

        outcome = classify_outcome(
            status=new_status,
            exit_code=task.exit_code,
            error_output=task.error_output,
        )

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
            response_action.status = new_status
            if task.output:
                response_action.output = task.output
            elif task.error_output:
                response_action.output = task.error_output
            if terminal:
                response_action.completed_at = task.completed_at or utcnow()
            db.add(response_action)

        remediation_updated = 0
        RemediationRun = _try_get_remediation_run_model()
        if RemediationRun is not None:
            try:
                runs = (
                    db.query(RemediationRun)
                    .filter(RemediationRun.task_id == str(task.id))
                    .all()
                )
                for run in runs:
                    if terminal:
                        run.status = "completed" if outcome["success"] else "failed"
                        run.completed_at = task.completed_at or utcnow()
                        if not outcome["success"]:
                            run.skip_reason = (
                                outcome.get("reason")
                                or payload.error_code
                                or "execution_failed"
                            )
                        details = dict(run.details or {})
                        details.update(
                            {
                                "exit_code": task.exit_code,
                                "outcome": outcome,
                                "error_code": payload.error_code,
                                "error_message": (payload.error_message or "")[:500] or None,
                                "stderr_preview": (task.error_output or "")[:500] or None,
                            }
                        )
                        run.details = details
                    elif new_status == "running":
                        details = dict(run.details or {})
                        details["agent_status"] = "running"
                        run.details = details
                    db.add(run)
                    remediation_updated += 1
            except Exception:
                logger.exception(
                    "Optional RemediationRun sync failed for task_id=%s", task_id
                )

        log_result = new_status
        if outcome["failed"]:
            log_result = f"failed:{outcome.get('reason') or 'unknown'}"
        db.add(
            AutomationLog(
                action="automation.task_state",
                result=(log_result or new_status)[:255],
            )
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        response_data: dict[str, Any] = {
            "task_id": str(task.id),
            "status": task.status,
            "exit_code": task.exit_code,
            "outcome": outcome,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
        if response_action is not None:
            response_data["response_action_status"] = response_action.status
        if remediation_updated:
            response_data["remediation_runs_updated"] = remediation_updated

        message = "task state updated"
        if outcome["failed"]:
            message = f"task failed ({outcome.get('reason') or 'execution_failed'})"
        elif outcome["success"]:
            message = "task completed successfully"

        return AutomationResponse(
            status=task.status,
            message=message,
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update script task state task_id=%s", task_id)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task state",
        )
