from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.software_deployment import (
    DeploymentEventResponse,
    DeploymentJobCreate,
    DeploymentJobResponse,
    DeploymentJobSummary,
    DeploymentJobUpdate,
    DeploymentTargetResponse,
    RollbackRequest,
    SoftwarePackageCreate,
    SoftwarePackageResponse,
    SoftwarePackageUpdate,
    TargetReportRequest,
)
from app.services.software_deployment_service import SoftwareDeploymentService

router = APIRouter(prefix="/software-deployment", tags=["Software Deployment"])


# =========================================================
# Application repository
# =========================================================

@router.post(
    "/packages",
    response_model=SoftwarePackageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_package(payload: SoftwarePackageCreate, db: Session = Depends(get_db)):
    return SoftwareDeploymentService(db).create_package(payload)


@router.get("/packages", response_model=list[SoftwarePackageResponse])
def list_packages(
    package_type: str | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    return SoftwareDeploymentService(db).list_packages(
        package_type=package_type, active_only=active_only
    )


@router.get("/packages/{package_id}", response_model=SoftwarePackageResponse)
def get_package(package_id: UUID, db: Session = Depends(get_db)):
    pkg = SoftwareDeploymentService(db).get_package(package_id)
    if not pkg:
        raise HTTPException(404, "Package not found")
    return pkg


@router.patch("/packages/{package_id}", response_model=SoftwarePackageResponse)
def update_package(
    package_id: UUID, payload: SoftwarePackageUpdate, db: Session = Depends(get_db)
):
    pkg = SoftwareDeploymentService(db).update_package(package_id, payload)
    if not pkg:
        raise HTTPException(404, "Package not found")
    return pkg


@router.delete("/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(package_id: UUID, db: Session = Depends(get_db)):
    if not SoftwareDeploymentService(db).delete_package(package_id):
        raise HTTPException(404, "Package not found")


# =========================================================
# Deployment jobs
# =========================================================

@router.post(
    "/jobs",
    response_model=DeploymentJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(payload: DeploymentJobCreate, db: Session = Depends(get_db)):
    try:
        return SoftwareDeploymentService(db).create_job(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/jobs", response_model=list[DeploymentJobResponse])
def list_jobs(
    status: str | None = None,
    package_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return SoftwareDeploymentService(db).list_jobs(status=status, package_id=package_id)


@router.get("/jobs/{job_id}", response_model=DeploymentJobResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = SoftwareDeploymentService(db).get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.patch("/jobs/{job_id}", response_model=DeploymentJobResponse)
def update_job(
    job_id: UUID, payload: DeploymentJobUpdate, db: Session = Depends(get_db)
):
    job = SoftwareDeploymentService(db).update_job(job_id, payload)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/jobs/{job_id}/start", response_model=DeploymentJobResponse)
def start_job(job_id: UUID, db: Session = Depends(get_db)):
    try:
        job = SoftwareDeploymentService(db).start_job(job_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=DeploymentJobResponse)
def cancel_job(job_id: UUID, db: Session = Depends(get_db)):
    job = SoftwareDeploymentService(db).cancel_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/jobs/{job_id}/summary", response_model=DeploymentJobSummary)
def job_summary(job_id: UUID, db: Session = Depends(get_db)):
    summary = SoftwareDeploymentService(db).job_summary(job_id)
    if not summary:
        raise HTTPException(404, "Job not found")
    return summary


@router.get("/jobs/{job_id}/events", response_model=list[DeploymentEventResponse])
def list_events(job_id: UUID, db: Session = Depends(get_db)):
    if not SoftwareDeploymentService(db).get_job(job_id):
        raise HTTPException(404, "Job not found")
    return SoftwareDeploymentService(db).list_events(job_id)


@router.post(
    "/jobs/{job_id}/rollback",
    response_model=DeploymentJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def rollback_job(
    job_id: UUID, payload: RollbackRequest, db: Session = Depends(get_db)
):
    try:
        return SoftwareDeploymentService(db).create_rollback(job_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


# =========================================================
# Agent reporting + instruction payload
# =========================================================

@router.post(
    "/jobs/{job_id}/targets/{target_id}/report",
    response_model=DeploymentTargetResponse,
)
def report_target(
    job_id: UUID,
    target_id: UUID,
    payload: TargetReportRequest,
    db: Session = Depends(get_db),
):
    try:
        return SoftwareDeploymentService(db).report_target(job_id, target_id, payload)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/jobs/{job_id}/targets/{target_id}/payload")
def agent_payload(job_id: UUID, target_id: UUID, db: Session = Depends(get_db)):
    try:
        return SoftwareDeploymentService(db).agent_payload(job_id, target_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
