from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.backup_integration import (
    BACKUP_PROVIDERS,
    BackupJob,
    BackupProvider,
    ProtectedResource,
    RestoreJob,
)
from app.schemas.backup_integration import (
    BackupFleetSummary,
    BackupJobCreate,
    BackupJobUpdate,
    BackupProviderCreate,
    BackupProviderUpdate,
    ProtectedResourceCreate,
    ProtectedResourceUpdate,
    RestoreJobCreate,
    RestoreJobUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


PROVIDER_CATALOG: list[dict[str, str]] = [
    {"provider_key": "veeam", "display_name": "Veeam"},
    {"provider_key": "datto", "display_name": "Datto"},
    {"provider_key": "acronis", "display_name": "Acronis"},
    {"provider_key": "azure_backup", "display_name": "Azure Backup"},
    {"provider_key": "backblaze", "display_name": "Backblaze"},
    {"provider_key": "onedrive", "display_name": "OneDrive"},
    {"provider_key": "google_drive", "display_name": "Google Drive"},
]


class BackupIntegrationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- Catalog / providers ----------

    def list_catalog(self) -> list[dict[str, str]]:
        return list(PROVIDER_CATALOG)

    def seed_providers(self, tenant_id: UUID | None = None) -> list[BackupProvider]:
        created: list[BackupProvider] = []
        for item in PROVIDER_CATALOG:
            q = self.db.query(BackupProvider).filter(
                BackupProvider.provider_key == item["provider_key"]
            )
            if tenant_id:
                q = q.filter(BackupProvider.tenant_id == tenant_id)
            if q.first():
                continue
            row = BackupProvider(
                provider_key=item["provider_key"],
                display_name=item["display_name"],
                enabled=False,
                tenant_id=tenant_id,
                last_sync_status="never",
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for r in created:
            self.db.refresh(r)
        return created

    def create_provider(self, payload: BackupProviderCreate) -> BackupProvider:
        key = payload.provider_key.strip().lower()
        if key not in BACKUP_PROVIDERS and key not in {
            p["provider_key"] for p in PROVIDER_CATALOG
        }:
            pass  # allow extension keys
        row = BackupProvider(
            provider_key=key,
            display_name=payload.display_name,
            enabled=payload.enabled,
            config=payload.config,
            notes=payload.notes,
            tenant_id=payload.tenant_id,
            last_sync_status="never",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_providers(
        self, *, enabled_only: bool = False, tenant_id: UUID | None = None
    ) -> list[BackupProvider]:
        q = self.db.query(BackupProvider)
        if enabled_only:
            q = q.filter(BackupProvider.enabled.is_(True))
        if tenant_id:
            q = q.filter(BackupProvider.tenant_id == tenant_id)
        return q.order_by(BackupProvider.display_name.asc()).all()

    def get_provider(self, provider_id: UUID) -> BackupProvider | None:
        return self.db.get(BackupProvider, provider_id)

    def update_provider(
        self, provider_id: UUID, payload: BackupProviderUpdate
    ) -> BackupProvider | None:
        row = self.get_provider(provider_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_provider(self, provider_id: UUID) -> bool:
        row = self.get_provider(provider_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ---------- Protected resources ----------

    def create_resource(self, payload: ProtectedResourceCreate) -> ProtectedResource:
        if not self.get_provider(payload.provider_id):
            raise ValueError("Provider not found")
        row = ProtectedResource(**payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_resources(
        self,
        *,
        provider_id: UUID | None = None,
        device_id: UUID | None = None,
        status: str | None = None,
    ) -> list[ProtectedResource]:
        q = self.db.query(ProtectedResource).options(
            joinedload(ProtectedResource.provider)
        )
        if provider_id:
            q = q.filter(ProtectedResource.provider_id == provider_id)
        if device_id:
            q = q.filter(ProtectedResource.device_id == device_id)
        if status:
            q = q.filter(ProtectedResource.status == status)
        return q.order_by(ProtectedResource.name.asc()).all()

    def update_resource(
        self, resource_id: UUID, payload: ProtectedResourceUpdate
    ) -> ProtectedResource | None:
        row = self.db.get(ProtectedResource, resource_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_resource(self, resource_id: UUID) -> bool:
        row = self.db.get(ProtectedResource, resource_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ---------- Backup jobs ----------

    def create_job(self, payload: BackupJobCreate) -> BackupJob:
        if not self.get_provider(payload.provider_id):
            raise ValueError("Provider not found")
        row = BackupJob(**payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_jobs(
        self,
        *,
        provider_id: UUID | None = None,
        resource_id: UUID | None = None,
        status: str | None = None,
    ) -> list[BackupJob]:
        q = self.db.query(BackupJob).options(joinedload(BackupJob.provider))
        if provider_id:
            q = q.filter(BackupJob.provider_id == provider_id)
        if resource_id:
            q = q.filter(BackupJob.resource_id == resource_id)
        if status:
            q = q.filter(BackupJob.status == status)
        return q.order_by(BackupJob.created_at.desc()).all()

    def update_job(self, job_id: UUID, payload: BackupJobUpdate) -> BackupJob | None:
        row = self.db.get(BackupJob, job_id)
        if not row:
            return None
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(row, k, v)

        # Keep protected resource last-backup fields in sync on terminal success
        if data.get("status") == "success" and row.resource_id:
            res = self.db.get(ProtectedResource, row.resource_id)
            if res:
                res.last_backup_at = row.finished_at or _utcnow()
                res.last_backup_status = "success"
                if row.bytes_processed is not None:
                    res.last_backup_bytes = row.bytes_processed
                res.status = "protected"

        self.db.commit()
        self.db.refresh(row)
        return row

    def start_job(self, job_id: UUID) -> BackupJob | None:
        row = self.db.get(BackupJob, job_id)
        if not row:
            return None
        if row.status not in ("pending", "cancelled"):
            raise ValueError(f"Cannot start job in status '{row.status}'")
        row.status = "running"
        row.started_at = _utcnow()
        row.error_message = None
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_job(self, job_id: UUID) -> bool:
        row = self.db.get(BackupJob, job_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ---------- Restore automation ----------

    def create_restore(self, payload: RestoreJobCreate) -> RestoreJob:
        if not self.get_provider(payload.provider_id):
            raise ValueError("Provider not found")
        row = RestoreJob(**payload.model_dump())
        if row.auto_start:
            row.status = "queued"
            # Automation engine would pick this up; mark ready for worker
            automation = dict(row.automation or {})
            automation.setdefault("queued_at", _utcnow().isoformat())
            automation.setdefault("steps", ["validate_source", "restore", "verify"])
            if automation.get("verify") is None:
                automation["verify"] = True
            row.automation = automation
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_restores(
        self,
        *,
        provider_id: UUID | None = None,
        status: str | None = None,
        device_id: UUID | None = None,
    ) -> list[RestoreJob]:
        q = self.db.query(RestoreJob).options(joinedload(RestoreJob.provider))
        if provider_id:
            q = q.filter(RestoreJob.provider_id == provider_id)
        if status:
            q = q.filter(RestoreJob.status == status)
        if device_id:
            q = q.filter(RestoreJob.device_id == device_id)
        return q.order_by(RestoreJob.created_at.desc()).all()

    def update_restore(
        self, restore_id: UUID, payload: RestoreJobUpdate
    ) -> RestoreJob | None:
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def start_restore(self, restore_id: UUID) -> RestoreJob | None:
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None
        if row.status not in ("pending", "queued", "cancelled"):
            raise ValueError(f"Cannot start restore in status '{row.status}'")
        row.status = "running"
        row.started_at = _utcnow()
        row.error_message = None
        automation = dict(row.automation or {})
        automation["started_at"] = row.started_at.isoformat()
        automation["current_step"] = "restore"
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def complete_restore(
        self,
        restore_id: UUID,
        *,
        success: bool = True,
        bytes_restored: int | None = None,
        error_message: str | None = None,
    ) -> RestoreJob | None:
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None
        row.status = "success" if success else "failed"
        row.finished_at = _utcnow()
        row.bytes_restored = bytes_restored
        row.error_message = error_message
        automation = dict(row.automation or {})
        automation["finished_at"] = row.finished_at.isoformat()
        if success and automation.get("verify"):
            automation["verify_status"] = "passed"
        if success and automation.get("notify"):
            automation["notify_queued"] = True
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_restore(self, restore_id: UUID) -> bool:
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ---------- Fleet summary ----------

    def fleet_summary(self) -> BackupFleetSummary:
        providers = self.list_providers(enabled_only=True)
        resources = self.list_resources()
        since = _utcnow() - timedelta(hours=24)
        jobs = (
            self.db.query(BackupJob)
            .filter(BackupJob.created_at >= since)
            .all()
        )
        restores_open = (
            self.db.query(RestoreJob)
            .filter(RestoreJob.status.in_(["pending", "queued", "running"]))
            .count()
        )
        return BackupFleetSummary(
            providers_enabled=len(providers),
            resources_total=len(resources),
            resources_protected=sum(1 for r in resources if r.status == "protected"),
            resources_at_risk=sum(1 for r in resources if r.status == "at_risk"),
            jobs_success_24h=sum(1 for j in jobs if j.status == "success"),
            jobs_failed_24h=sum(1 for j in jobs if j.status == "failed"),
            restores_open=restores_open,
        )
