from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.software_deployment import (
    DeploymentEvent,
    DeploymentJob,
    DeploymentTarget,
    SoftwarePackage,
)
from app.schemas.software_deployment import (
    DeploymentJobCreate,
    DeploymentJobSummary,
    DeploymentJobUpdate,
    RollbackRequest,
    SoftwarePackageCreate,
    SoftwarePackageUpdate,
    TargetReportRequest,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SoftwareDeploymentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _event(
        self,
        job_id: UUID,
        message: str,
        *,
        level: str = "info",
        target_id: UUID | None = None,
        detail: dict | None = None,
    ) -> None:
        self.db.add(
            DeploymentEvent(
                job_id=job_id,
                target_id=target_id,
                level=level,
                message=message,
                detail=detail,
            )
        )

    def _recompute_job_counts(self, job: DeploymentJob) -> None:
        targets = (
            self.db.query(DeploymentTarget)
            .filter(DeploymentTarget.job_id == job.id)
            .all()
        )
        job.targets_total = len(targets)
        job.targets_success = sum(1 for t in targets if t.status == "success")
        job.targets_failed = sum(1 for t in targets if t.status == "failed")
        job.targets_pending = sum(
            1
            for t in targets
            if t.status in ("pending", "downloading", "installing", "queued")
        )

        if job.targets_total > 0 and job.targets_pending == 0:
            if job.targets_failed == 0:
                job.status = "completed"
            elif job.targets_success == 0:
                job.status = "failed"
            else:
                job.status = "completed"  # partial success still completed
            if job.finished_at is None:
                job.finished_at = _utcnow()

    # ---------- Application repository ----------

    def create_package(self, payload: SoftwarePackageCreate) -> SoftwarePackage:
        data = payload.model_dump()
        if not data.get("success_exit_codes"):
            data["success_exit_codes"] = [0]
        pkg = SoftwarePackage(**data)
        self.db.add(pkg)
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def list_packages(
        self,
        *,
        package_type: str | None = None,
        active_only: bool = False,
    ) -> list[SoftwarePackage]:
        q = self.db.query(SoftwarePackage)
        if package_type:
            q = q.filter(SoftwarePackage.package_type == package_type)
        if active_only:
            q = q.filter(SoftwarePackage.is_active.is_(True))
        return q.order_by(SoftwarePackage.name.asc(), SoftwarePackage.version.desc()).all()

    def get_package(self, package_id: UUID) -> SoftwarePackage | None:
        return self.db.get(SoftwarePackage, package_id)

    def update_package(
        self, package_id: UUID, payload: SoftwarePackageUpdate
    ) -> SoftwarePackage | None:
        pkg = self.get_package(package_id)
        if not pkg:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(pkg, k, v)
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def delete_package(self, package_id: UUID) -> bool:
        pkg = self.get_package(package_id)
        if not pkg:
            return False
        # Soft-delete preferred if jobs exist
        has_jobs = (
            self.db.query(DeploymentJob)
            .filter(DeploymentJob.package_id == package_id)
            .first()
        )
        if has_jobs:
            pkg.is_active = False
            self.db.commit()
            return True
        self.db.delete(pkg)
        self.db.commit()
        return True

    # ---------- Jobs ----------

    def create_job(self, payload: DeploymentJobCreate) -> DeploymentJob:
        pkg = self.get_package(payload.package_id)
        if not pkg or not pkg.is_active:
            raise ValueError("Package not found or inactive")

        job = DeploymentJob(
            package_id=payload.package_id,
            name=payload.name,
            action=payload.action,
            status="queued",
            created_by=payload.created_by,
            notes=payload.notes,
            scheduled_at=payload.scheduled_at,
            tenant_id=payload.tenant_id,
            tags=payload.tags,
            targets_total=0,
            targets_pending=0,
        )
        self.db.add(job)
        self.db.flush()

        device_ids = list(payload.device_ids or [])
        hostnames = list(payload.hostnames or [])

        for did in device_ids:
            self.db.add(
                DeploymentTarget(
                    job_id=job.id,
                    device_id=did,
                    status="pending",
                )
            )
        for hn in hostnames:
            self.db.add(
                DeploymentTarget(
                    job_id=job.id,
                    hostname=hn,
                    status="pending",
                )
            )

        self._recompute_job_counts(job)
        self._event(
            job.id,
            f"Job created action={job.action} package={pkg.name}@{pkg.version} "
            f"type={pkg.package_type} targets={job.targets_total}",
            detail={"package_type": pkg.package_type, "action": job.action},
        )
        self.db.commit()
        return self.get_job(job.id)  # type: ignore[return-value]

    def list_jobs(
        self,
        *,
        status: str | None = None,
        package_id: UUID | None = None,
    ) -> list[DeploymentJob]:
        q = self.db.query(DeploymentJob)
        if status:
            q = q.filter(DeploymentJob.status == status)
        if package_id:
            q = q.filter(DeploymentJob.package_id == package_id)
        return q.order_by(DeploymentJob.created_at.desc()).all()

    def get_job(self, job_id: UUID) -> DeploymentJob | None:
        return (
            self.db.query(DeploymentJob)
            .options(joinedload(DeploymentJob.targets))
            .filter(DeploymentJob.id == job_id)
            .first()
        )

    def update_job(
        self, job_id: UUID, payload: DeploymentJobUpdate
    ) -> DeploymentJob | None:
        job = self.db.get(DeploymentJob, job_id)
        if not job:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(job, k, v)
        self.db.commit()
        return self.get_job(job_id)

    def start_job(self, job_id: UUID) -> DeploymentJob | None:
        job = self.get_job(job_id)
        if not job:
            return None
        if job.status not in ("pending", "queued"):
            raise ValueError(f"Cannot start job in status={job.status}")
        job.status = "running"
        job.started_at = _utcnow()
        self._event(job.id, "Job started")
        self.db.commit()
        return self.get_job(job_id)

    def cancel_job(self, job_id: UUID) -> DeploymentJob | None:
        job = self.get_job(job_id)
        if not job:
            return None
        job.status = "cancelled"
        job.finished_at = _utcnow()
        for t in job.targets:
            if t.status in ("pending", "downloading", "installing"):
                t.status = "skipped"
        self._recompute_job_counts(job)
        self._event(job.id, "Job cancelled")
        self.db.commit()
        return self.get_job(job_id)

    def job_summary(self, job_id: UUID) -> DeploymentJobSummary | None:
        job = self.db.get(DeploymentJob, job_id)
        if not job:
            return None
        total = job.targets_total or 0
        rate = (job.targets_success / total * 100.0) if total else 0.0
        return DeploymentJobSummary(
            job_id=job.id,
            status=job.status,
            targets_total=job.targets_total,
            targets_success=job.targets_success,
            targets_failed=job.targets_failed,
            targets_pending=job.targets_pending,
            success_rate=round(rate, 2),
            finished_at=job.finished_at,
        )

    # ---------- Success reporting (agent callback) ----------

    def report_target(
        self, job_id: UUID, target_id: UUID, payload: TargetReportRequest
    ) -> DeploymentTarget:
        target = (
            self.db.query(DeploymentTarget)
            .filter(
                DeploymentTarget.id == target_id,
                DeploymentTarget.job_id == job_id,
            )
            .first()
        )
        if not target:
            raise ValueError("Target not found")

        job = self.db.get(DeploymentJob, job_id)
        if not job:
            raise ValueError("Job not found")

        if job.status == "queued":
            job.status = "running"
            job.started_at = job.started_at or _utcnow()

        target.status = payload.status
        target.exit_code = payload.exit_code
        target.stdout = payload.stdout
        target.stderr = payload.stderr
        target.error_message = payload.error_message
        target.download_bytes = payload.download_bytes
        target.duration_ms = payload.duration_ms
        target.reboot_required = payload.reboot_required
        target.reported_at = _utcnow()
        if payload.status in ("downloading", "installing") and target.started_at is None:
            target.started_at = _utcnow()
        if payload.status in ("success", "failed", "rolled_back", "skipped"):
            target.finished_at = _utcnow()

        self._event(
            job_id,
            f"Target {target.hostname or target.device_id} → {payload.status}",
            level="error" if payload.status == "failed" else "info",
            target_id=target.id,
            detail={"exit_code": payload.exit_code, "status": payload.status},
        )
        self._recompute_job_counts(job)
        self.db.commit()
        self.db.refresh(target)
        return target

    # ---------- Rollback ----------

    def create_rollback(
        self, job_id: UUID, payload: RollbackRequest
    ) -> DeploymentJob:
        original = self.get_job(job_id)
        if not original:
            raise ValueError("Original job not found")
        pkg = self.get_package(original.package_id)
        if not pkg:
            raise ValueError("Package not found")
        if not pkg.uninstall_command and not pkg.uninstall_args and not pkg.choco_id and not pkg.winget_id:
            raise ValueError(
                "Package has no uninstall/rollback definition "
                "(uninstall_command, uninstall_args, choco_id, or winget_id)"
            )

        # Targets to roll back: successful ones from original, optionally filtered
        candidates = [t for t in original.targets if t.status == "success"]
        if payload.device_ids:
            wanted = set(payload.device_ids)
            candidates = [t for t in candidates if t.device_id in wanted]

        if not candidates:
            raise ValueError("No successful targets available to roll back")

        rb = DeploymentJob(
            package_id=original.package_id,
            name=f"Rollback: {original.name}",
            action="rollback",
            status="queued",
            created_by=payload.created_by,
            notes=payload.notes or f"Rollback of job {original.id}",
            rollback_of_job_id=original.id,
            tenant_id=original.tenant_id,
        )
        self.db.add(rb)
        self.db.flush()

        for t in candidates:
            self.db.add(
                DeploymentTarget(
                    job_id=rb.id,
                    device_id=t.device_id,
                    hostname=t.hostname,
                    agent_id=t.agent_id,
                    status="pending",
                )
            )

        self._recompute_job_counts(rb)
        original.status = "rolled_back" if not payload.device_ids else original.status
        self._event(
            rb.id,
            f"Rollback job created for {len(candidates)} target(s) of {original.id}",
            detail={"original_job_id": str(original.id)},
        )
        self.db.commit()
        return self.get_job(rb.id)  # type: ignore[return-value]

    def list_events(self, job_id: UUID) -> list[DeploymentEvent]:
        return (
            self.db.query(DeploymentEvent)
            .filter(DeploymentEvent.job_id == job_id)
            .order_by(DeploymentEvent.created_at.asc())
            .all()
        )

    def agent_payload(self, job_id: UUID, target_id: UUID) -> dict:
        """Build the instruction payload an agent needs to execute."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError("Job not found")
        target = next((t for t in job.targets if t.id == target_id), None)
        if not target:
            raise ValueError("Target not found")
        pkg = self.get_package(job.package_id)
        if not pkg:
            raise ValueError("Package not found")

        return {
            "job_id": str(job.id),
            "target_id": str(target.id),
            "action": job.action,
            "package": {
                "id": str(pkg.id),
                "name": pkg.name,
                "version": pkg.version,
                "package_type": pkg.package_type,
                "source_url": pkg.source_url,
                "file_name": pkg.file_name,
                "sha256": pkg.sha256,
                "choco_id": pkg.choco_id,
                "winget_id": pkg.winget_id,
                "install_args": pkg.install_args,
                "uninstall_args": pkg.uninstall_args,
                "uninstall_command": pkg.uninstall_command,
                "success_exit_codes": pkg.success_exit_codes or [0],
                "requires_reboot": pkg.requires_reboot,
                "requires_elevation": pkg.requires_elevation,
                "timeout_seconds": pkg.timeout_seconds,
                "architecture": pkg.architecture,
            },
        }
