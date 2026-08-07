from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.models.backup_integration import RestoreJob
from app.schemas.backup_integration import (
    BackupFleetSummary,
    RestoreJobCreate,
    RestoreJobUpdate,
    RetryVerificationRequest,
    RunVerificationRequest,
    StartVerificationRequest,
    VerificationCheckResult,
    VerificationTimeoutSweepResult,
    VerificationWorkflow,
)
from app.services.backup_integration_helpers import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_VERIFICATION_TIMEOUT_SECONDS,
    VerificationRetryExhaustedError,
    VerificationTimeoutError,
    _build_verification,
    _is_timed_out,
    _iso,
    _summarize_checks,
    _utcnow,
)


class BackupVerificationMixin:
    """Timeout + retry verification workflows."""

    def create_restore(self, payload: RestoreJobCreate):
        if not self.get_provider(payload.provider_id):
            raise ValueError("Provider not found")
        data = payload.model_dump(exclude={
            "verify", "verification_policy", "verification_timeout_seconds",
            "verification_max_retries", "verification_auto_retry",
        })
        row = RestoreJob(**data)
        policy = payload.verification_policy or "standard"
        verify = payload.verify
        timeout = payload.verification_timeout_seconds or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
        max_retries = (
            payload.verification_max_retries
            if payload.verification_max_retries is not None
            else DEFAULT_MAX_RETRIES
        )
        auto_retry = bool(payload.verification_auto_retry)
        automation = dict(row.automation or {})
        automation.setdefault("steps", ["validate_source", "restore", "verify", "notify"])
        automation["verify"] = verify
        automation["verification"] = _build_verification(
            row.restore_type, policy, enabled=verify, timeout_seconds=timeout,
            max_retries=max_retries, auto_retry=auto_retry, attempt=1,
        )
        if row.auto_start:
            row.status = "queued"
            automation["queued_at"] = _iso()
        row.automation = automation
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_restores(self, *, provider_id=None, status=None, device_id=None):
        from sqlalchemy.orm import joinedload
        q = self.db.query(RestoreJob).options(joinedload(RestoreJob.provider))
        if provider_id:
            q = q.filter(RestoreJob.provider_id == provider_id)
        if status:
            q = q.filter(RestoreJob.status == status)
        if device_id:
            q = q.filter(RestoreJob.device_id == device_id)
        return q.order_by(RestoreJob.created_at.desc()).all()

    def get_restore(self, restore_id: UUID):
        return self.db.get(RestoreJob, restore_id)

    def update_restore(self, restore_id: UUID, payload: RestoreJobUpdate):
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def start_restore(self, restore_id: UUID):
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

    def _mark_verification_timed_out(self, row: RestoreJob, *, reason=None, auto_retry=True):
        automation = dict(row.automation or {})
        verification = dict(automation.get("verification") or {})
        now = _utcnow()
        timeout = int(verification.get("timeout_seconds") or DEFAULT_VERIFICATION_TIMEOUT_SECONDS)
        attempt = int(verification.get("attempt") or 1)
        max_retries = int(
            verification.get("max_retries")
            if verification.get("max_retries") is not None
            else DEFAULT_MAX_RETRIES
        )
        retries_remaining = max(0, max_retries - attempt)
        checks = list(verification.get("checks") or [])
        for c in checks:
            if c.get("status") in ("pending", "running"):
                c["status"] = "failed"
                c["message"] = reason or f"Verification timed out after {timeout}s"
                c["finished_at"] = _iso(now)
                if not c.get("started_at"):
                    c["started_at"] = c["finished_at"]
        msg = reason or f"Verification timed out after {timeout}s [attempt {attempt}/{max_retries + 1}]"
        history = list(verification.get("retry_history") or [])
        history.append({"attempt": attempt, "timed_out_at": _iso(now), "error": msg, "restarted_at": None})
        verification.update({
            "checks": checks,
            "summary": _summarize_checks(checks),
            "status": "timed_out",
            "timed_out_at": _iso(now),
            "timeout_error": msg,
            "finished_at": _iso(now),
            "retry_history": history,
            "retries_remaining": retries_remaining,
        })
        automation["verification"] = verification
        automation["current_step"] = "verify_timeout"
        automation["finished_at"] = _iso(now)
        row.status = "verify_failed"
        row.error_message = msg
        row.finished_at = now
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        if auto_retry and bool(verification.get("auto_retry")) and retries_remaining > 0:
            try:
                return self.retry_verification(row.id, RetryVerificationRequest(force=False))
            except (VerificationRetryExhaustedError, ValueError):
                return row
        return row

    def enforce_verification_timeout(self, restore_id: UUID, *, raise_on_timeout=False):
        row = self.db.get(RestoreJob, restore_id)
        if not row or row.status != "verifying":
            return row
        verification = (row.automation or {}).get("verification") or {}
        if not verification or verification.get("status") in ("passed", "failed", "skipped", "timed_out"):
            return row
        if not _is_timed_out(verification):
            return row
        row = self._mark_verification_timed_out(row)
        if raise_on_timeout:
            v = (row.automation or {}).get("verification") or {}
            remaining = int(v.get("retries_remaining") or 0)
            raise VerificationTimeoutError(
                row.error_message or "Verification timed out",
                restore_id=row.id,
                attempt=int(v.get("attempt") or 1),
                retries_remaining=remaining,
                can_retry=remaining > 0,
            )
        return row

    def complete_restore(self, restore_id: UUID, *, success=True, bytes_restored=None,
                         error_message=None, skip_verification=False):
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
        verify_enabled = bool(automation.get("verify", True)) and bool(verification.get("enabled", True))
        if verify_enabled and not skip_verification:
            row.status = "verifying"
            automation["current_step"] = "verify"
            if not verification.get("checks"):
                verification = _build_verification(
                    row.restore_type, verification.get("policy") or "standard", enabled=True,
                    timeout_seconds=verification.get("timeout_seconds"),
                    max_retries=verification.get("max_retries"),
                    auto_retry=bool(verification.get("auto_retry")),
                    attempt=int(verification.get("attempt") or 1),
                    retry_history=verification.get("retry_history"),
                )
            started = _utcnow()
            timeout = int(verification.get("timeout_seconds") or DEFAULT_VERIFICATION_TIMEOUT_SECONDS)
            verification["status"] = "running"
            verification["started_at"] = _iso(started)
            verification["timeout_seconds"] = timeout
            verification["deadline_at"] = _iso(started + timedelta(seconds=timeout))
            verification["timed_out_at"] = None
            verification["timeout_error"] = None
            verification.setdefault("attempt", 1)
            verification.setdefault("max_retries", DEFAULT_MAX_RETRIES)
            verification.setdefault("auto_retry", False)
            verification.setdefault("retry_history", [])
            verification["retries_remaining"] = max(
                0, int(verification.get("max_retries", DEFAULT_MAX_RETRIES))
                - (int(verification.get("attempt") or 1) - 1),
            )
            automation["verification"] = verification
            row.automation = automation
            self.db.commit()
            self.db.refresh(row)
            return row
        row.status = "success"
        row.finished_at = _utcnow()
        automation["current_step"] = "done"
        automation["finished_at"] = _iso(row.finished_at)
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_verification(self, restore_id: UUID):
        self.enforce_verification_timeout(restore_id)
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return None
        v = (row.automation or {}).get("verification")
        return VerificationWorkflow.model_validate(v) if v else None

    def start_verification(self, restore_id: UUID, payload: StartVerificationRequest | None = None):
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            raise ValueError("Restore not found")
        payload = payload or StartVerificationRequest()
        automation = dict(row.automation or {})
        verification = automation.get("verification") or {}
        if row.status in ("failed", "cancelled") and not payload.force:
            raise ValueError(f"Cannot verify restore in status '{row.status}' (use force=true)")
        policy = payload.policy or verification.get("policy") or "standard"
        timeout = payload.timeout_seconds or verification.get("timeout_seconds") or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
        max_retries = (
            payload.max_retries if payload.max_retries is not None
            else verification.get("max_retries", DEFAULT_MAX_RETRIES)
        )
        auto_retry = (
            payload.auto_retry if payload.auto_retry is not None
            else bool(verification.get("auto_retry"))
        )
        verification = _build_verification(
            row.restore_type, policy, enabled=True, timeout_seconds=int(timeout),
            max_retries=int(max_retries) if max_retries is not None else DEFAULT_MAX_RETRIES,
            auto_retry=bool(auto_retry), attempt=1, retry_history=[],
        )
        started = _utcnow()
        verification["status"] = "running"
        verification["started_at"] = _iso(started)
        verification["deadline_at"] = _iso(started + timedelta(seconds=int(timeout)))
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

    def retry_verification(self, restore_id: UUID, payload: RetryVerificationRequest | None = None):
        """Restart verification after timeout, consuming one retry slot."""
        payload = payload or RetryVerificationRequest()
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            raise ValueError("Restore not found")
        automation = dict(row.automation or {})
        verification = dict(automation.get("verification") or {})
        timed_out = verification.get("status") == "timed_out" or (
            row.status == "verify_failed" and verification.get("timed_out_at")
        )
        if not timed_out and not payload.force:
            raise ValueError("Retry only allowed after a verification timeout (or force=true)")
        attempt = int(verification.get("attempt") or 1)
        max_retries = int(
            verification.get("max_retries")
            if verification.get("max_retries") is not None
            else DEFAULT_MAX_RETRIES
        )
        next_attempt = attempt + 1
        if next_attempt > max_retries + 1 and not payload.force:
            raise VerificationRetryExhaustedError(
                f"Retry budget exhausted (attempt {next_attempt}, max_retries={max_retries})",
                restore_id=row.id,
            )
        policy = payload.policy or verification.get("policy") or "standard"
        timeout = int(
            payload.timeout_seconds
            or verification.get("timeout_seconds")
            or DEFAULT_VERIFICATION_TIMEOUT_SECONDS
        )
        history = list(verification.get("retry_history") or [])
        if history and history[-1].get("restarted_at") is None:
            history[-1]["restarted_at"] = _iso()
        verification = _build_verification(
            row.restore_type, policy, enabled=True, timeout_seconds=timeout,
            max_retries=max_retries, auto_retry=bool(verification.get("auto_retry")),
            attempt=next_attempt, retry_history=history,
        )
        started = _utcnow()
        verification["status"] = "running"
        verification["started_at"] = _iso(started)
        verification["deadline_at"] = _iso(started + timedelta(seconds=timeout))
        automation["verify"] = True
        automation["verification"] = verification
        automation["current_step"] = "verify"
        automation.pop("finished_at", None)
        row.status = "verifying"
        row.finished_at = None
        row.error_message = None
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def report_check(self, restore_id: UUID, result: VerificationCheckResult):
        row = self.enforce_verification_timeout(restore_id, raise_on_timeout=True)
        if not row:
            raise ValueError("Restore not found")
        if row.status == "verify_failed":
            v = (row.automation or {}).get("verification") or {}
            raise VerificationTimeoutError(
                row.error_message or "Verification timed out",
                restore_id=row.id,
                can_retry=int(v.get("retries_remaining") or 0) > 0,
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

    def run_verification(self, restore_id: UUID, payload: RunVerificationRequest | None = None):
        row = self.enforce_verification_timeout(restore_id, raise_on_timeout=True)
        if not row:
            raise ValueError("Restore not found")
        if row.status == "verify_failed" and (
            (row.automation or {}).get("verification") or {}
        ).get("status") == "timed_out":
            raise VerificationTimeoutError(
                row.error_message or "Verification timed out", restore_id=row.id
            )
        payload = payload or RunVerificationRequest()
        automation = dict(row.automation or {})
        verification = automation.get("verification") or _build_verification(
            row.restore_type, "standard", enabled=True
        )
        if verification.get("status") == "pending":
            started = _utcnow()
            timeout = int(verification.get("timeout_seconds") or DEFAULT_VERIFICATION_TIMEOUT_SECONDS)
            verification["status"] = "running"
            verification["started_at"] = _iso(started)
            verification["deadline_at"] = _iso(started + timedelta(seconds=timeout))
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
                    c["message"] = "Simulated fail" if c["status"] == "failed" else "Skipped"
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
                    f"Verification failed: {summary['required_failed']} required check(s) failed"
                )
                row.finished_at = _utcnow()
                automation["current_step"] = "verify_failed"
            else:
                verification["status"] = "passed"
                row.status = "success"
                row.error_message = None
                row.finished_at = _utcnow()
                automation["current_step"] = "done"
            automation["finished_at"] = _iso(row.finished_at)
        automation["verification"] = verification
        row.automation = automation
        self.db.commit()
        self.db.refresh(row)
        return row

    def skip_verification(self, restore_id: UUID, reason: str | None = None):
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            raise ValueError("Restore not found")
        automation = dict(row.automation or {})
        verification = automation.get("verification") or {}
        if verification.get("status") == "timed_out" or (
            row.status == "verify_failed" and verification.get("timed_out_at")
        ):
            raise VerificationTimeoutError(
                verification.get("timeout_error")
                or row.error_message
                or "Timed out; POST .../verification/retry",
                restore_id=row.id,
            )
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

    def sweep_verification_timeouts(self):
        open_rows = self.db.query(RestoreJob).filter(RestoreJob.status == "verifying").all()
        timed_out_ids, retried_ids = [], []
        for row in open_rows:
            before = row.status
            updated = self.enforce_verification_timeout(row.id)
            if not updated:
                continue
            if updated.status == "verifying" and before == "verifying":
                v = (updated.automation or {}).get("verification") or {}
                if int(v.get("attempt") or 1) > 1:
                    retried_ids.append(updated.id)
            elif updated.status == "verify_failed" and before == "verifying":
                timed_out_ids.append(updated.id)
        return VerificationTimeoutSweepResult(
            scanned=len(open_rows),
            timed_out=len(timed_out_ids),
            auto_retried=len(retried_ids),
            restore_ids=timed_out_ids,
            retried_ids=retried_ids,
        )

    def delete_restore(self, restore_id: UUID) -> bool:
        row = self.db.get(RestoreJob, restore_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def fleet_summary(self):
        from app.models.backup_integration import BackupJob
        providers = self.list_providers(enabled_only=True)
        resources = self.list_resources()
        since = _utcnow() - timedelta(hours=24)
        jobs = self.db.query(BackupJob).filter(BackupJob.created_at >= since).all()
        restores_open = self.db.query(RestoreJob).filter(
            RestoreJob.status.in_(["pending", "queued", "running", "verifying"])
        ).count()
        restores_verifying = self.db.query(RestoreJob).filter(RestoreJob.status == "verifying").count()
        restores_verify_failed = self.db.query(RestoreJob).filter(
            RestoreJob.status == "verify_failed"
        ).count()
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
