"""Device health snapshot API + daily report."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.device_health_service import DeviceHealthService

router = APIRouter(prefix="/device-health", tags=["Device Health"])


@router.get("/report/daily")
def daily_device_health_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """On-demand daily device health report for the current tenant."""
    from app.services.device_health_report import build_device_health_daily_report

    tid = getattr(current_user, "tenant_id", None)
    return build_device_health_daily_report(db, tenant_id=tid)


@router.post("/report/daily/run")
def run_and_store_daily_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a stored ReportRun for today's device health summary."""
    from app.models.reporting import ReportRun, ReportTemplate
    from app.services.device_health_report import build_device_health_daily_report
    from app.services.reporting_service import ReportingService

    tid = getattr(current_user, "tenant_id", None)
    data = build_device_health_daily_report(db, tenant_id=tid)

    try:
        ReportingService(db).seed_templates(tenant_id=None)
    except Exception:
        pass

    tpl = (
        db.query(ReportTemplate)
        .filter(ReportTemplate.template_key == "device_health_daily")
        .first()
    )

    now = datetime.now(timezone.utc)
    run = ReportRun(
        tenant_id=tid,
        name="Daily Device Health Report",
        report_type="device_health",
        template_id=tpl.id if tpl else None,
        format="json",
        status="completed",
        parameters={},
        result_data=data,
        triggered_by=getattr(current_user, "email", None) or "api",
        started_at=now,
    )
    if hasattr(ReportRun, "completed_at"):
        run.completed_at = now
    if hasattr(ReportRun, "finished_at"):
        run.finished_at = now
    db.add(run)
    db.commit()
    db.refresh(run)
    return {
        "ok": True,
        "run_id": str(run.id),
        "status": run.status,
        "summary": data.get("summary"),
        "worst_devices": data.get("worst_devices"),
    }


@router.post("/recompute-stale")
def recompute_stale(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin-triggered pass of missed-heartbeat processing."""
    stats = DeviceHealthService(db).process_stale_endpoints()
    return {"ok": True, **stats}


@router.get("/{device_id}")
def get_device_health(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snap = DeviceHealthService(db).get_health_snapshot(device_id)
    if not snap:
        raise HTTPException(404, "Device/agent not found or invalid id")
    return snap
