from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.reporting import (
    AssetReportSummary,
    ExecutiveDashboard,
    PatchComplianceSummary,
    ReportDefinitionCreate,
    ReportDefinitionResponse,
    ReportDefinitionUpdate,
    ReportRunCreate,
    ReportRunResponse,
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportScheduleUpdate,
    ReportTemplateCreate,
    ReportTemplateResponse,
    ReportTemplateUpdate,
    SecurityComplianceSummary,
)
from app.services.reporting_service import ReportingService

router = APIRouter(prefix="/reports", tags=["Reporting"])


class ReportEmailRequest(BaseModel):
    recipients: list[str] = Field(..., min_length=1)
    schedule_name: str | None = None


@router.get("/catalog")
def get_catalog(db: Session = Depends(get_db)):
    return ReportingService(db).list_catalog()


@router.post(
    "/templates/seed",
    response_model=list[ReportTemplateResponse],
    status_code=201,
)
def seed_templates(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    return ReportingService(db).seed_templates(tenant_id=tenant_id)


@router.get("/dashboards/executive", response_model=ExecutiveDashboard)
def executive_dashboard(
    tenant_id: UUID | None = None, db: Session = Depends(get_db)
):
    return ReportingService(db).executive_dashboard(tenant_id=tenant_id)


@router.get("/summaries/patch-compliance", response_model=PatchComplianceSummary)
def patch_compliance_summary(
    tenant_id: UUID | None = None, db: Session = Depends(get_db)
):
    return ReportingService(db).patch_compliance_summary(tenant_id=tenant_id)


@router.get(
    "/summaries/security-compliance", response_model=SecurityComplianceSummary
)
def security_compliance_summary(
    tenant_id: UUID | None = None, db: Session = Depends(get_db)
):
    return ReportingService(db).security_compliance_summary(tenant_id=tenant_id)


@router.get("/summaries/assets", response_model=AssetReportSummary)
def asset_summary(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    return ReportingService(db).asset_summary(tenant_id=tenant_id)


@router.post("/templates", response_model=ReportTemplateResponse, status_code=201)
def create_template(payload: ReportTemplateCreate, db: Session = Depends(get_db)):
    return ReportingService(db).create_template(payload)


@router.get("/templates", response_model=list[ReportTemplateResponse])
def list_templates(
    enabled_only: bool = False,
    report_type: str | None = None,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return ReportingService(db).list_templates(
        enabled_only=enabled_only, report_type=report_type, tenant_id=tenant_id
    )


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
def get_template(template_id: UUID, db: Session = Depends(get_db)):
    row = ReportingService(db).get_template(template_id)
    if not row:
        raise HTTPException(404, "Template not found")
    return row


@router.patch("/templates/{template_id}", response_model=ReportTemplateResponse)
def update_template(
    template_id: UUID, payload: ReportTemplateUpdate, db: Session = Depends(get_db)
):
    row = ReportingService(db).update_template(template_id, payload)
    if not row:
        raise HTTPException(404, "Template not found")
    return row


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: UUID, db: Session = Depends(get_db)):
    if not ReportingService(db).delete_template(template_id):
        raise HTTPException(404, "Template not found")


@router.post("/definitions", response_model=ReportDefinitionResponse, status_code=201)
def create_definition(payload: ReportDefinitionCreate, db: Session = Depends(get_db)):
    return ReportingService(db).create_definition(payload)


@router.get("/definitions", response_model=list[ReportDefinitionResponse])
def list_definitions(
    tenant_id: UUID | None = None,
    report_type: str | None = None,
    db: Session = Depends(get_db),
):
    return ReportingService(db).list_definitions(
        tenant_id=tenant_id, report_type=report_type
    )


@router.get("/definitions/{definition_id}", response_model=ReportDefinitionResponse)
def get_definition(definition_id: UUID, db: Session = Depends(get_db)):
    row = ReportingService(db).get_definition(definition_id)
    if not row:
        raise HTTPException(404, "Definition not found")
    return row


@router.patch("/definitions/{definition_id}", response_model=ReportDefinitionResponse)
def update_definition(
    definition_id: UUID,
    payload: ReportDefinitionUpdate,
    db: Session = Depends(get_db),
):
    row = ReportingService(db).update_definition(definition_id, payload)
    if not row:
        raise HTTPException(404, "Definition not found")
    return row


@router.delete("/definitions/{definition_id}", status_code=204)
def delete_definition(definition_id: UUID, db: Session = Depends(get_db)):
    if not ReportingService(db).delete_definition(definition_id):
        raise HTTPException(404, "Definition not found")


@router.post("/runs", response_model=ReportRunResponse, status_code=201)
def create_run(payload: ReportRunCreate, db: Session = Depends(get_db)):
    try:
        return ReportingService(db).create_run(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/runs", response_model=list[ReportRunResponse])
def list_runs(
    tenant_id: UUID | None = None,
    report_type: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return ReportingService(db).list_runs(
        tenant_id=tenant_id, report_type=report_type, status=status, limit=limit
    )


@router.get("/runs/{run_id}", response_model=ReportRunResponse)
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    row = ReportingService(db).get_run(run_id)
    if not row:
        raise HTTPException(404, "Run not found")
    return row


@router.post("/runs/{run_id}/execute", response_model=ReportRunResponse)
def execute_run(run_id: UUID, db: Session = Depends(get_db)):
    try:
        return ReportingService(db).execute_run(run_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/runs/{run_id}/download")
def download_run(run_id: UUID, db: Session = Depends(get_db)):
    result = ReportingService(db).get_run_bytes(run_id)
    if not result:
        raise HTTPException(404, "Report not ready or not found")
    content, content_type, filename = result
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/runs/{run_id}/email")
def email_run(
    run_id: UUID,
    payload: ReportEmailRequest,
    db: Session = Depends(get_db),
):
    """Send a completed report run to the given recipients."""
    try:
        return ReportingService(db).deliver_run_email(
            run_id,
            recipients=payload.recipients,
            schedule_name=payload.schedule_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: UUID, db: Session = Depends(get_db)):
    if not ReportingService(db).delete_run(run_id):
        raise HTTPException(404, "Run not found")


@router.post("/schedules", response_model=ReportScheduleResponse, status_code=201)
def create_schedule(payload: ReportScheduleCreate, db: Session = Depends(get_db)):
    try:
        return ReportingService(db).create_schedule(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/schedules", response_model=list[ReportScheduleResponse])
def list_schedules(
    tenant_id: UUID | None = None,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    return ReportingService(db).list_schedules(
        tenant_id=tenant_id, enabled_only=enabled_only
    )


@router.get("/schedules/{schedule_id}", response_model=ReportScheduleResponse)
def get_schedule(schedule_id: UUID, db: Session = Depends(get_db)):
    row = ReportingService(db).get_schedule(schedule_id)
    if not row:
        raise HTTPException(404, "Schedule not found")
    return row


@router.patch("/schedules/{schedule_id}", response_model=ReportScheduleResponse)
def update_schedule(
    schedule_id: UUID, payload: ReportScheduleUpdate, db: Session = Depends(get_db)
):
    row = ReportingService(db).update_schedule(schedule_id, payload)
    if not row:
        raise HTTPException(404, "Schedule not found")
    return row


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: UUID, db: Session = Depends(get_db)):
    if not ReportingService(db).delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")


@router.post("/schedules/process-due", response_model=list[ReportRunResponse])
def process_due_schedules(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
):
    """Worker/cron entrypoint: execute due scheduled reports and email recipients."""
    return ReportingService(db).process_due_schedules(limit=limit)


@router.post("/schedules/{schedule_id}/send-now")
def schedule_send_now(schedule_id: UUID, db: Session = Depends(get_db)):
    """Run a schedule immediately and email recipients if configured."""
    svc = ReportingService(db)
    sched = svc.get_schedule(schedule_id)
    if not sched:
        raise HTTPException(404, "Schedule not found")
    run = svc.create_run(
        ReportRunCreate(
            name=sched.name,
            template_id=sched.template_id,
            definition_id=sched.definition_id,
            format=sched.format,
            parameters=sched.parameters,
            tenant_id=sched.tenant_id,
            triggered_by=f"manual:{schedule_id}",
            run_now=True,
        )
    )
    run.schedule_id = schedule_id
    db.commit()
    delivery = None
    if run.status == "completed" and sched.recipients:
        try:
            delivery = svc.deliver_run_email(
                run.id,
                recipients=list(sched.recipients or []),
                schedule_name=sched.name,
            )
        except ValueError as e:
            delivery = {"ok": False, "error": str(e)}
    return {"run_id": str(run.id), "run_status": run.status, "email": delivery}


@router.get("/email/status")
def email_status():
    """SMTP configuration status (no secrets)."""
    from app.core.config import settings
    from app.services.email_service import EmailService

    svc = EmailService()
    return {
        "enabled": settings.SMTP_ENABLED,
        "configured": svc.configured,
        "host": settings.SMTP_HOST or None,
        "port": settings.SMTP_PORT,
        "from_email": settings.SMTP_FROM_EMAIL or None,
        "from_name": settings.SMTP_FROM_NAME,
        "use_tls": settings.SMTP_USE_TLS,
        "use_ssl": settings.SMTP_USE_SSL,
        "has_credentials": bool(settings.SMTP_USERNAME),
    }
