from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
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
    RunVerificationRequest,
    StartVerificationRequest,
    VerificationCheckResult,
    VerificationTimeoutSweepResult,
    VerificationWorkflow,
)

# Default verification window once verification starts (1 hour)
DEFAULT_VERIFICATION_TIMEOUT_SECONDS = 3600


class VerificationTimeoutError(ValueError):
    """Raised when a verification workflow has exceeded its deadline."""

    def __init__(self, message: str, restore_id: UUID | None = None) -> None:
        super().__init__(message)
        self.restore_id = restore_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Support trailing Z
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


PROVIDER_CATALOG: list[dict[str, str]] = [
    {"provider_key": "veeam", "display_name": "Veeam"},
    {"provider_key": "datto", "display_name": "Datto"},
    {"provider_key": "acronis", "display_name": "Acronis"},
    {"provider_key": "azure_backup", "display_name": "Azure Backup"},
    {"provider_key": "backblaze", "display_name": "Backblaze"},
    {"provider_key": "onedrive", "display_name": "OneDrive"},
    {"provider_key": "google_drive", "display_name": "Google Drive"},
]

_BASE_CHECKS: dict[str, list[dict[str, Any]]] = {
    "file": [
        {
            "id": "path_exists",
            "name": "Target path exists",
            "description": "Restored path is present on the target",
            "required": True,
        },
        {
            "id": "size_nonzero",
            "name": "Non-zero size",
            "description": "Restored object has content",
            "required": True,
        },
        {
            "id": "checksum_match",
            "name": "Checksum match",
            "description": "Hash matches backup catalog when available",
            "required": False,
        },
    ],
    "folder": [
        {
            "id": "path_exists",
            "name": "Folder exists",
            "description": "Restored folder is present",
            "required": True,
        },
        {
            "id": "child_count",
            "name": "Child objects present",
            "description": "Folder contains expected children",
            "required": True,
        },
        {
            "id": "permissions_ok",
            "name": "Permissions intact",
            "description": "ACL/ownership roughly preserved",
            "required": False,
        },
    ],
    "volume": [
        {
            "id": "volume_mounted",
            "name": "Volume mounted",
            "description": "Restored volume is mounted and readable",
            "required": True,
        },
        {
            "id": "filesystem_clean",
            "name": "Filesystem clean",
            "description": "No critical FS errors on restored volume",
            "required": True,
        },
        {
            "id": "boot_sector",
            "name": "Boot metadata",
            "description": "Boot sector / EFI data present if applicable",
            "required": False,
        },
    ],
    "full_system": [
        {
            "id": "boot_check",
            "name": "System boots",
            "description": "Restored system reaches OS",
            "required": True,
        },
        {
            "id": "service_health",
            "name": "Critical services",
            "description": "Core services are running",
            "required": True,
        },
        {
            "id": "network_up",
            "name": "Network stack",
            "description": "NIC has link / IP",
            "required": True,
        },
        {
            "id": "agent_heartbeat",
            "name": "RMM agent heartbeat",
            "description": "Bhudi agent reports healthy after restore",
            "required": False,
        },
    ],
    "mailbox": [
        {
            "id": "mailbox_accessible",
            "name": "Mailbox accessible",
            "description": "Mailbox opens in provider API",
            "required": True,
        },
        {
            "id": "item_sample",
            "name": "Sample items readable",
            "description": "Sample messages/folders open",
            "required": True,
        },
    ],
    "database": [
        {
            "id": "db_online",
            "name": "Database online",
            "description": "Engine reports DB online",
            "required": True,
        },
        {
            "id": "connection_test",
            "name": "Connection test",
            "description": "Can open a client connection",
            "required": True,
        },
        {
            "id": "row_sample",
            "name": "Row sample",
            "description": "SELECT sample succeeds",
            "required": False,
        },
    ],
}


def _checks_for(restore_type: str, policy: str) -> list[dict[str, Any]]:
    base = list(_BASE_CHECKS.get(restore_type, _BASE_CHECKS["file"]))
    if policy == "quick":
        base = [c for c in base if c.get("required")]
    elif policy == "strict":
        base = [{**c, "required": True} for c in base]
    return base


def _build_verification(
    restore_type: str,
    policy: str,
    enabled: bool = True,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    checks = []
    for c in _checks_for(restore_type, policy):
        checks.append(
            {
                "id": c["id"],
                "name": c["name"],
                "description": c.get("description"),
                "required": bool(c.get("required", True)),
                "status": "pending",
                "message": None,
                "evidence": None,
                "started_at": None,
                "finished_at": None,
            }
        )
    timeout = timeout_seconds or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
    if timeout < 60:
        timeout = 60
    if timeout > 86400:
        timeout = 86400
    return {
        "enabled": enabled,
        "policy": policy,
        "status": "pending" if enabled else "skipped",
        "started_at": None,
        "finished_at": None,
        "timeout_seconds": timeout,
        "deadline_at": None,
        "timed_out_at": None,
        "timeout_error": None,
        "checks": checks,
        "summary": _summarize_checks(checks),
    }


def _summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    total = len(checks)
    passed = sum(1 for c in checks if c.get("status") == "passed")
    failed = sum(1 for c in checks if c.get("status") == "failed")
    skipped = sum(1 for c in checks if c.get("status") == "skipped")
    pending = sum(1 for c in checks if c.get("status") in ("pending", "running"))
    required_failed = sum(
        1 for c in checks if c.get("required") and c.get("status") == "failed"
    )
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pending": pending,
        "required_failed": required_failed,
    }


def _verification_deadline(verification: dict[str, Any]) -> datetime | None:
    """Compute deadline from explicit deadline_at or started_at + timeout."""
    explicit = _parse_iso(verification.get("deadline_at"))
    if explicit:
        return explicit
    started = _parse_iso(verification.get("started_at"))
    if not started:
        return None
    timeout = int(
        verification.get("timeout_seconds") or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
    )
    return started + timedelta(seconds=timeout)


def _is_timed_out(verification: dict[str, Any], now: datetime | None = None) -> bool:
    if verification.get("status") in ("passed", "failed", "skipped", "timed_out"):
        return verification.get("status") == "timed_out"
    deadline = _verification_deadline(verification)
    if not deadline:
        return False
    return (now or _utcnow()) > deadline


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

    # ---------- Restore + verification ----------

    def create_restore(self, payload: RestoreJobCreate) -> RestoreJob:
        if not self.get_provider(payload.provider_id):
            raise ValueError("Provider not found")

        data = payload.model_dump(
            exclude={"verify", "verification_policy", "verification_timeout_seconds"}
        )
        row = RestoreJob(**data)

        policy = payload.verification_policy or "standard"
        verify = payload.verify
        timeout = payload.verification_timeout_seconds or DEFAULT_VERIFICATION_TIMEOUT_SECONDS

        automation = dict(row.automation or {})
        automation.setdefault(
            "steps", ["validate_source", "restore", "verify", "notify"]
        )
        automation["verify"] = verify
        automation["verification"] = _build_verification(
            row.restore_type, policy, enabled=verify, timeout_seconds=timeout
        )

        if row.auto_start:
            row.status = "queued"
            automation["queued_at"] = _iso()

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

    def get_restore(self, restore_id: UUID) -> RestoreJob | None:
        return self.db.get(RestoreJob, restore_id)

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
        automation["started_at"] = _iso(row.started_at)
        automation["current_step"] = "restore"
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def _mark_verification_timed_out(
        self, row: RestoreJob, *, reason: str | None = None
    ) -> RestoreJob:
        """Terminal failure path for verification timeout."""
        automation = dict(row.automation or {})
        verification = dict(automation.get("verification") or {})
        now = _utcnow()
        timeout = int(
            verification.get("timeout_seconds") or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
        )
        deadline = _verification_deadline(verification)

        checks = list(verification.get("checks") or [])
        for c in checks:
            if c.get("status") in ("pending", "running"):
                c["status"] = "failed"
                c["message"] = reason or (
                    f"Verification timed out after {timeout}s "
                    f"(check still {c.get('status')})"
                )
                c["finished_at"] = _iso(now)
                if not c.get("started_at"):
                    c["started_at"] = c["finished_at"]

        msg = reason or (
            f"Verification timed out after {timeout} seconds"
            + (f" (deadline {deadline.isoformat()})" if deadline else "")
        )

        verification["checks"] = checks
        verification["summary"] = _summarize_checks(checks)
        verification["status"] = "timed_out"
        verification["timed_out_at"] = _iso(now)
        verification["timeout_error"] = msg
        verification["finished_at"] = _iso(now)
        if deadline and not verification.get("deadline_at"):
            verification["deadline_at"] = deadline.isoformat()

        automation["verification"] = verification
        automation["current_step"] = "verify_timeout"
        automation["finished_at"] = _iso(now)

        row.status = "verify_failed"
        row.error_message = msg
        row.finished_at = now
        row.automation = automation

        self.db.commit()
        self.db.refresh(row)
        return row

    def enforce_verification_timeout(
        self, restore_id: UUID, *, raise_on_timeout: bool = False
    ) -> RestoreJob | None:
        """
        If verification is past its deadline, mark timed_out / verify_failed.

        When raise_on_timeout is True, raises VerificationTimeoutError after persisting.
        """
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None

        if row.status != "verifying":
            return row

        automation = dict(row.automation or {})
        verification = automation.get("verification") or {}
        if not verification or verification.get("status") in (
            "passed",
            "failed",
            "skipped",
            "timed_out",
        ):
            return row

        if not _is_timed_out(verification):
            return row

        row = self._mark_verification_timed_out(row)
        if raise_on_timeout:
            raise VerificationTimeoutError(
                row.error_message or "Verification timed out",
                restore_id=row.id,
            )
        return row

    def complete_restore(
        self,
        restore_id: UUID,
        *,
        success: bool = True,
        bytes_restored: int | None = None,
        error_message: str | None = None,
        skip_verification: bool = False,
    ) -> RestoreJob | None:
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None

        row.bytes_restored = bytes_restored
        automation = dict(row.automation or {})
        automation["restore_finished_at"] = _iso()

        if not success:
            row.status = "failed"
            row.finished_at = _utcnow()
            row.error_message = error_message or "Restore failed"
            automation["current_step"] = "failed"
            automation["finished_at"] = _iso(row.finished_at)
            row.automation = automation
            self.db.commit()
            self.db.refresh(row)
            return row

        row.error_message = None
        verification = automation.get("verification") or {}
        verify_enabled = bool(automation.get("verify", True)) and bool(
            verification.get("enabled", True)
        )

        if verify_enabled and not skip_verification:
            row.status = "verifying"
            automation["current_step"] = "verify"
            if not verification.get("checks"):
                policy = verification.get("policy") or "standard"
                timeout = verification.get("timeout_seconds")
                verification = _build_verification(
                    row.restore_type,
                    policy,
                    enabled=True,
                    timeout_seconds=timeout,
                )
            started = _utcnow()
            timeout = int(
                verification.get("timeout_seconds")
                or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
            )
            verification["status"] = "running"
            verification["started_at"] = _iso(started)
            verification["timeout_seconds"] = timeout
            verification["deadline_at"] = _iso(started + timedelta(seconds=timeout))
            verification["timed_out_at"] = None
            verification["timeout_error"] = None
            automation["verification"] = verification
            row.automation = automation
            self.db.commit()
            self.db.refresh(row)
            return row

        row.status = "success"
        row.finished_at = _utcnow()
        automation["current_step"] = "done"
        automation["finished_at"] = _iso(row.finished_at)
        if automation.get("notify"):
            automation["notify_queued"] = True
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_verification(self, restore_id: UUID) -> VerificationWorkflow | None:
        # Auto-enforce timeout so reads stay consistent
        self.enforce_verification_timeout(restore_id)
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None
        automation = dict(row.automation or {})
        v = automation.get("verification")
        if not v:
            return None
        return VerificationWorkflow.model_validate(v)

    def start_verification(
        self, restore_id: UUID, payload: StartVerificationRequest | None = None
    ) -> RestoreJob:
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            raise ValueError("Restore not found")

        payload = payload or StartVerificationRequest()
        automation = dict(row.automation or {})
        verification = automation.get("verification") or {}

        if row.status in ("failed", "cancelled") and not payload.force:
            raise ValueError(
                f"Cannot verify restore in status '{row.status}' (use force=true)"
            )

        policy = payload.policy or verification.get("policy") or "standard"
        timeout = (
            payload.timeout_seconds
            or verification.get("timeout_seconds")
            or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
        )
        verification = _build_verification(
            row.restore_type, policy, enabled=True, timeout_seconds=int(timeout)
        )
        started = _utcnow()
        verification["status"] = "running"
        verification["started_at"] = _iso(started)
        verification["deadline_at"] = _iso(
            started + timedelta(seconds=int(timeout))
        )

        automation["verify"] = True
        automation["verification"] = verification
        automation["current_step"] = "verify"
        row.status = "verifying"
        row.finished_at = None
        row.error_message = None
        row.automation = automation

        self.db.commit()
        self.db.refresh(row)
        return row

    def report_check(
        self, restore_id: UUID, result: VerificationCheckResult
    ) -> RestoreJob:
        row = self.enforce_verification_timeout(restore_id, raise_on_timeout=True)
        if not row:
            raise ValueError("Restore not found")

        if row.status == "verify_failed":
            raise VerificationTimeoutError(
                row.error_message or "Verification timed out",
                restore_id=row.id,
            )

        automation = dict(row.automation or {})
        verification = automation.get("verification")
        if not verification:
            raise ValueError("No verification workflow on this restore")

        if verification.get("status") == "timed_out":
            raise VerificationTimeoutError(
                verification.get("timeout_error") or "Verification timed out",
                restore_id=row.id,
            )

        checks = list(verification.get("checks") or [])
        found = False
        for c in checks:
            if c.get("id") == result.check_id:
                c["status"] = result.status
                c["message"] = result.message
                c["evidence"] = result.evidence
                c["finished_at"] = _iso()
                if not c.get("started_at"):
                    c["started_at"] = c["finished_at"]
                found = True
                break
        if not found:
            raise ValueError(f"Unknown check_id '{result.check_id}'")

        verification["checks"] = checks
        verification["summary"] = _summarize_checks(checks)
        automation["verification"] = verification
        row.automation = automation

        self.db.commit()
        self.db.refresh(row)
        return row

    def run_verification(
        self, restore_id: UUID, payload: RunVerificationRequest | None = None
    ) -> RestoreJob:
        row = self.enforce_verification_timeout(restore_id, raise_on_timeout=True)
        if not row:
            raise ValueError("Restore not found")

        if row.status == "verify_failed" and (
            (row.automation or {}).get("verification") or {}
        ).get("status") == "timed_out":
            raise VerificationTimeoutError(
                row.error_message or "Verification timed out",
                restore_id=row.id,
            )

        payload = payload or RunVerificationRequest()
        automation = dict(row.automation or {})
        verification = automation.get("verification")
        if not verification or not verification.get("enabled", True):
            verification = _build_verification(
                row.restore_type, "standard", enabled=True
            )

        if verification.get("status") == "pending":
            started = _utcnow()
            timeout = int(
                verification.get("timeout_seconds")
                or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
            )
            verification["status"] = "running"
            verification["started_at"] = _iso(started)
            verification["deadline_at"] = _iso(
                started + timedelta(seconds=timeout)
            )

        checks = list(verification.get("checks") or [])
        by_id = {c["id"]: c for c in checks}

        if payload.results:
            for r in payload.results:
                c = by_id.get(r.check_id)
                if not c:
                    continue
                c["status"] = r.status
                c["message"] = r.message
                c["evidence"] = r.evidence
                c["finished_at"] = _iso()
                if not c.get("started_at"):
                    c["started_at"] = c["finished_at"]
        else:
            for c in checks:
                if c.get("status") in ("passed", "failed", "skipped"):
                    continue
                c["started_at"] = _iso()
                if payload.simulate_pass:
                    c["status"] = "passed"
                    c["message"] = "Simulated pass"
                else:
                    c["status"] = "failed" if c.get("required") else "skipped"
                    c["message"] = (
                        "Simulated fail" if c["status"] == "failed" else "Skipped"
                    )
                c["finished_at"] = _iso()

        verification["checks"] = checks
        summary = _summarize_checks(checks)
        verification["summary"] = summary

        if summary["pending"] == 0:
            verification["finished_at"] = _iso()
            if summary["required_failed"] > 0:
                verification["status"] = "failed"
                row.status = "verify_failed"
                row.error_message = (
                    f"Verification failed: {summary['required_failed']} "
                    f"required check(s) failed"
                )
                row.finished_at = _utcnow()
                automation["current_step"] = "verify_failed"
            else:
                verification["status"] = "passed"
                row.status = "success"
                row.error_message = None
                row.finished_at = _utcnow()
                automation["current_step"] = "done"
                if automation.get("notify"):
                    automation["notify_queued"] = True
            automation["finished_at"] = _iso(row.finished_at)

        automation["verification"] = verification
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def skip_verification(self, restore_id: UUID, reason: str | None = None) -> RestoreJob:
        # Allow skip even after timeout? Only if still verifying — timeout already terminal
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            raise ValueError("Restore not found")

        # If already timed out, do not silently convert to success
        automation = dict(row.automation or {})
        verification = automation.get("verification") or {}
        if verification.get("status") == "timed_out" or (
            row.status == "verify_failed" and verification.get("timed_out_at")
        ):
            raise VerificationTimeoutError(
                verification.get("timeout_error")
                or row.error_message
                or "Verification already timed out; restart verification to retry",
                restore_id=row.id,
            )

        # Enforce timeout first if still open
        if row.status == "verifying" and _is_timed_out(verification):
            return self._mark_verification_timed_out(row)

        checks = list(verification.get("checks") or [])
        for c in checks:
            if c.get("status") in ("pending", "running"):
                c["status"] = "skipped"
                c["message"] = reason or "Verification skipped by operator"
                c["finished_at"] = _iso()
        verification["checks"] = checks
        verification["status"] = "skipped"
        verification["finished_at"] = _iso()
        verification["summary"] = _summarize_checks(checks)
        verification["skip_reason"] = reason

        automation["verification"] = verification
        automation["verify"] = False
        automation["current_step"] = "done"
        automation["finished_at"] = _iso()

        if row.status in ("verifying", "running", "queued", "pending"):
            row.status = "success"
        row.finished_at = _utcnow()
        row.automation = automation

        self.db.commit()
        self.db.refresh(row)
        return row

    def sweep_verification_timeouts(self) -> VerificationTimeoutSweepResult:
        """Batch job: expire all open verifying restores past deadline."""
        open_rows = (
            self.db.query(RestoreJob)
            .filter(RestoreJob.status == "verifying")
            .all()
        )
        timed_out_ids: list[UUID] = []
        for row in open_rows:
            before = row.status
            updated = self.enforce_verification_timeout(row.id)
            if updated and updated.status == "verify_failed" and before == "verifying":
                timed_out_ids.append(updated.id)
        return VerificationTimeoutSweepResult(
            scanned=len(open_rows),
            timed_out=len(timed_out_ids),
            restore_ids=timed_out_ids,
        )

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
            .filter(RestoreJob.status.in_(["pending", "queued", "running", "verifying"]))
            .count()
        )
        restores_verifying = (
            self.db.query(RestoreJob)
            .filter(RestoreJob.status == "verifying")
            .count()
        )
        restores_verify_failed = (
            self.db.query(RestoreJob)
            .filter(RestoreJob.status == "verify_failed")
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
            restores_verifying=restores_verifying,
            restores_verify_failed=restores_verify_failed,
        )
