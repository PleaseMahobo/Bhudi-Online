from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.backup_integration import (
    BackupFleetSummary,
    BackupJobCreate,
    BackupJobResponse,
    BackupJobUpdate,
    BackupProviderCreate,
    BackupProviderResponse,
    BackupProviderUpdate,
    ProtectedResourceCreate,
    ProtectedResourceResponse,
    ProtectedResourceUpdate,
    RestoreJobCreate,
    RestoreJobResponse,
    RestoreJobUpdate,
)
from app.services.backup_integration_service import (
    PROVIDER_CATALOG,
    BackupIntegrationService,
)

router = APIRouter(prefix="/backup", tags=["Backup Integration"])


def _resource_resp(row) -> ProtectedResourceResponse:
    data = ProtectedResourceResponse.model_validate(row)
    if row.provider:
        data.provider_key = row.provider.provider_key
    return data


def _job_resp(row) -> BackupJobResponse:
    data = BackupJobResponse.model_validate(row)
    if row.provider:
        data.provider_key = row.provider.provider_key
    return data


def _restore_resp(row) -> RestoreJobResponse:
    data = RestoreJobResponse.model_validate(row)
    if row.provider:
        data.provider_key = row.provider.provider_key
    return data


# ---------- Catalog / providers ----------

@router.get("/catalog")
def list_catalog():
    return PROVIDER_CATALOG


@router.post(
    "/providers/seed",
    response_model=list[BackupProviderResponse],
    status_code=status.HTTP_201_CREATED,
)
def seed_providers(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    return BackupIntegrationService(db).seed_providers(tenant_id=tenant_id)


@router.post(
    "/providers",
    response_model=BackupProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_provider(payload: BackupProviderCreate, db: Session = Depends(get_db)):
    return BackupIntegrationService(db).create_provider(payload)


@router.get("/providers", response_model=list[BackupProviderResponse])
def list_providers(
    enabled_only: bool = False,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return BackupIntegrationService(db).list_providers(
        enabled_only=enabled_only, tenant_id=tenant_id
    )


@router.get("/providers/{provider_id}", response_model=BackupProviderResponse)
def get_provider(provider_id: UUID, db: Session = Depends(get_db)):
    row = BackupIntegrationService(db).get_provider(provider_id)
    if not row:
        raise HTTPException(404, "Provider not found")
    return row


@router.patch("/providers/{provider_id}", response_model=BackupProviderResponse)
def update_provider(
    provider_id: UUID, payload: BackupProviderUpdate, db: Session = Depends(get_db)
):
    row = BackupIntegrationService(db).update_provider(provider_id, payload)
    if not row:
        raise HTTPException(404, "Provider not found")
    return row


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: UUID, db: Session = Depends(get_db)):
    if not BackupIntegrationService(db).delete_provider(provider_id):
        raise HTTPException(404, "Provider not found")


# ---------- Resources ----------

@router.post(
    "/resources",
    response_model=ProtectedResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resource(payload: ProtectedResourceCreate, db: Session = Depends(get_db)):
    try:
        row = BackupIntegrationService(db).create_resource(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    rows = BackupIntegrationService(db).list_resources()
    row = next((r for r in rows if r.id == row.id), row)
    return _resource_resp(row)


@router.get("/resources", response_model=list[ProtectedResourceResponse])
def list_resources(
    provider_id: UUID | None = None,
    device_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    rows = BackupIntegrationService(db).list_resources(
        provider_id=provider_id, device_id=device_id, status=status
    )
    return [_resource_resp(r) for r in rows]


@router.patch("/resources/{resource_id}", response_model=ProtectedResourceResponse)
def update_resource(
    resource_id: UUID,
    payload: ProtectedResourceUpdate,
    db: Session = Depends(get_db),
):
    row = BackupIntegrationService(db).update_resource(resource_id, payload)
    if not row:
        raise HTTPException(404, "Resource not found")
    rows = BackupIntegrationService(db).list_resources()
    row = next((r for r in rows if r.id == row.id), row)
    return _resource_resp(row)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: UUID, db: Session = Depends(get_db)):
    if not BackupIntegrationService(db).delete_resource(resource_id):
        raise HTTPException(404, "Resource not found")


# ---------- Backup jobs ----------

@router.post(
    "/jobs",
    response_model=BackupJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(payload: BackupJobCreate, db: Session = Depends(get_db)):
    try:
        row = BackupIntegrationService(db).create_job(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    rows = BackupIntegrationService(db).list_jobs()
    row = next((j for j in rows if j.id == row.id), row)
    return _job_resp(row)


@router.get("/jobs", response_model=list[BackupJobResponse])
def list_jobs(
    provider_id: UUID | None = None,
    resource_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    rows = BackupIntegrationService(db).list_jobs(
        provider_id=provider_id, resource_id=resource_id, status=status
    )
    return [_job_resp(r) for r in rows]


@router.patch("/jobs/{job_id}", response_model=BackupJobResponse)
def update_job(
    job_id: UUID, payload: BackupJobUpdate, db: Session = Depends(get_db)
):
    row = BackupIntegrationService(db).update_job(job_id, payload)
    if not row:
        raise HTTPException(404, "Job not found")
    rows = BackupIntegrationService(db).list_jobs()
    row = next((j for j in rows if j.id == row.id), row)
    return _job_resp(row)


@router.post("/jobs/{job_id}/start", response_model=BackupJobResponse)
def start_job(job_id: UUID, db: Session = Depends(get_db)):
    try:
        row = BackupIntegrationService(db).start_job(job_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not row:
        raise HTTPException(404, "Job not found")
    rows = BackupIntegrationService(db).list_jobs()
    row = next((j for j in rows if j.id == row.id), row)
    return _job_resp(row)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    if not BackupIntegrationService(db).delete_job(job_id):
        raise HTTPException(404, "Job not found")


# ---------- Restore automation ----------

@router.post(
    "/restores",
    response_model=RestoreJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restore(payload: RestoreJobCreate, db: Session = Depends(get_db)):
    try:
        row = BackupIntegrationService(db).create_restore(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    rows = BackupIntegrationService(db).list_restores()
    row = next((r for r in rows if r.id == row.id), row)
    return _restore_resp(row)


@router.get("/restores", response_model=list[RestoreJobResponse])
def list_restores(
    provider_id: UUID | None = None,
    status: str | None = None,
    device_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    rows = BackupIntegrationService(db).list_restores(
        provider_id=provider_id, status=status, device_id=device_id
    )
    return [_restore_resp(r) for r in rows]


@router.patch("/restores/{restore_id}", response_model=RestoreJobResponse)
def update_restore(
    restore_id: UUID, payload: RestoreJobUpdate, db: Session = Depends(get_db)
):
    row = BackupIntegrationService(db).update_restore(restore_id, payload)
    if not row:
        raise HTTPException(404, "Restore not found")
    rows = BackupIntegrationService(db).list_restores()
    row = next((r for r in rows if r.id == row.id), row)
    return _restore_resp(row)


@router.post("/restores/{restore_id}/start", response_model=RestoreJobResponse)
def start_restore(restore_id: UUID, db: Session = Depends(get_db)):
    try:
        row = BackupIntegrationService(db).start_restore(restore_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not row:
        raise HTTPException(404, "Restore not found")
    rows = BackupIntegrationService(db).list_restores()
    row = next((r for r in rows if r.id == row.id), row)
    return _restore_resp(row)


@router.post("/restores/{restore_id}/complete", response_model=RestoreJobResponse)
def complete_restore(
    restore_id: UUID,
    success: bool = True,
    bytes_restored: int | None = None,
    error_message: str | None = None,
    db: Session = Depends(get_db),
):
    row = BackupIntegrationService(db).complete_restore(
        restore_id,
        success=success,
        bytes_restored=bytes_restored,
        error_message=error_message,
    )
    if not row:
        raise HTTPException(404, "Restore not found")
    rows = BackupIntegrationService(db).list_restores()
    row = next((r for r in rows if r.id == row.id), row)
    return _restore_resp(row)


@router.delete("/restores/{restore_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restore(restore_id: UUID, db: Session = Depends(get_db)):
    if not BackupIntegrationService(db).delete_restore(restore_id):
        raise HTTPException(404, "Restore not found")


# ---------- Summary ----------

@router.get("/summary", response_model=BackupFleetSummary)
def fleet_summary(db: Session = Depends(get_db)):
    return BackupIntegrationService(db).fleet_summary()
