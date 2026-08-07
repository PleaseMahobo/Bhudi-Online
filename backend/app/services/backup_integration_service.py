from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.backup_integration import (
    BackupJob, BackupProvider, ProtectedResource, RestoreJob,
)
from app.schemas.backup_integration import (
    BackupFleetSummary, BackupJobCreate, BackupJobUpdate,
    BackupProviderCreate, BackupProviderUpdate,
    ProtectedResourceCreate, ProtectedResourceUpdate,
    RestoreJobCreate, RestoreJobUpdate,
    RetryVerificationRequest, RunVerificationRequest, StartVerificationRequest,
    VerificationCheckResult, VerificationTimeoutSweepResult, VerificationWorkflow,
)
from app.services.backup_integration_helpers import (
    DEFAULT_MAX_RETRIES, DEFAULT_VERIFICATION_TIMEOUT_SECONDS, PROVIDER_CATALOG,
    VerificationRetryExhaustedError, VerificationTimeoutError,
    _build_verification, _is_timed_out, _iso, _summarize_checks, _utcnow,
    _verification_deadline,
)

# Full implementation restored in subsequent commit via helpers + this module.
# See backup_integration_helpers.py for timeout/retry primitives.

class BackupIntegrationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_catalog(self):
        return list(PROVIDER_CATALOG)

    def seed_providers(self, tenant_id: UUID | None = None):
        created = []
        for item in PROVIDER_CATALOG:
            q = self.db.query(BackupProvider).filter(BackupProvider.provider_key == item["provider_key"])
            if tenant_id:
                q = q.filter(BackupProvider.tenant_id == tenant_id)
            if q.first():
                continue
            row = BackupProvider(provider_key=item["provider_key"], display_name=item["display_name"],
                                 enabled=False, tenant_id=tenant_id, last_sync_status="never")
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for r in created:
            self.db.refresh(r)
        return created

    def create_provider(self, payload: BackupProviderCreate):
        row = BackupProvider(provider_key=payload.provider_key.strip().lower(), display_name=payload.display_name,
                             enabled=payload.enabled, config=payload.config, notes=payload.notes,
                             tenant_id=payload.tenant_id, last_sync_status="never")
        self.db.add(row); self.db.commit(); self.db.refresh(row); return row

    def list_providers(self, *, enabled_only=False, tenant_id=None):
        q = self.db.query(BackupProvider)
        if enabled_only: q = q.filter(BackupProvider.enabled.is_(True))
        if tenant_id: q = q.filter(BackupProvider.tenant_id == tenant_id)
        return q.order_by(BackupProvider.display_name.asc()).all()

    def get_provider(self, provider_id: UUID):
        return self.db.get(BackupProvider, provider_id)

    def update_provider(self, provider_id: UUID, payload: BackupProviderUpdate):
        row = self.get_provider(provider_id)
        if not row: return None
        for k, v in payload.model_dump(exclude_unset=True).items(): setattr(row, k, v)
        self.db.commit(); self.db.refresh(row); return row

    def delete_provider(self, provider_id: UUID) -> bool:
        row = self.get_provider(provider_id)
        if not row: return False
        self.db.delete(row); self.db.commit(); return True

    def create_resource(self, payload: ProtectedResourceCreate):
        if not self.get_provider(payload.provider_id): raise ValueError("Provider not found")
        row = ProtectedResource(**payload.model_dump())
        self.db.add(row); self.db.commit(); self.db.refresh(row); return row

    def list_resources(self, *, provider_id=None, device_id=None, status=None):
        q = self.db.query(ProtectedResource).options(joinedload(ProtectedResource.provider))
        if provider_id: q = q.filter(ProtectedResource.provider_id == provider_id)
        if device_id: q = q.filter(ProtectedResource.device_id == device_id)
        if status: q = q.filter(ProtectedResource.status == status)
        return q.order_by(ProtectedResource.name.asc()).all()

    def update_resource(self, resource_id: UUID, payload: ProtectedResourceUpdate):
        row = self.db.get(ProtectedResource, resource_id)
        if not row: return None
        for k, v in payload.model_dump(exclude_unset=True).items(): setattr(row, k, v)
        self.db.commit(); self.db.refresh(row); return row

    def delete_resource(self, resource_id: UUID) -> bool:
        row = self.db.get(ProtectedResource, resource_id)
        if not row: return False
        self.db.delete(row); self.db.commit(); return True

    def create_job(self, payload: BackupJobCreate):
        if not self.get_provider(payload.provider_id): raise ValueError("Provider not found")
        row = BackupJob(**payload.model_dump())
        self.db.add(row); self.db.commit(); self.db.refresh(row); return row

    def list_jobs(self, *, provider_id=None, resource_id=None, status=None):
        q = self.db.query(BackupJob).options(joinedload(BackupJob.provider))
        if provider_id: q = q.filter(BackupJob.provider_id == provider_id)
        if resource_id: q = q.filter(BackupJob.resource_id == resource_id)
        if status: q = q.filter(BackupJob.status == status)
        return q.order_by(BackupJob.created_at.desc()).all()

    def update_job(self, job_id: UUID, payload: BackupJobUpdate):
        row = self.db.get(BackupJob, job_id)
        if not row: return None
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items(): setattr(row, k, v)
        if data.get("status") == "success" and row.resource_id:
            res = self.db.get(ProtectedResource, row.resource_id)
            if res:
                res.last_backup_at = row.finished_at or _utcnow()
                res.last_backup_status = "success"
                if row.bytes_processed is not None: res.last_backup_bytes = row.bytes_processed
                res.status = "protected"
        self.db.commit(); self.db.refresh(row); return row

    def start_job(self, job_id: UUID):
        row = self.db.get(BackupJob, job_id)
        if not row: return None
        if row.status not in ("pending", "cancelled"):
            raise ValueError(f"Cannot start job in status '{row.status}'")
        row.status = "running"; row.started_at = _utcnow(); row.error_message = None
        self.db.commit(); self.db.refresh(row); return row

    def delete_job(self, job_id: UUID) -> bool:
        row = self.db.get(BackupJob, job_id)
        if not row: return False
        self.db.delete(row); self.db.commit(); return True
