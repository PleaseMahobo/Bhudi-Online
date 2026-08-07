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
    RetryVerificationRequest,
    RunVerificationRequest,
    StartVerificationRequest,
    VerificationCheckResult,
    VerificationTimeoutSweepResult,
    VerificationWorkflow,
)

DEFAULT_VERIFICATION_TIMEOUT_SECONDS = 3600
DEFAULT_MAX_RETRIES = 3


class VerificationTimeoutError(ValueError):
    def __init__(
        self,
        message: str,
        restore_id: UUID | None = None,
        *,
        attempt: int | None = None,
        retries_remaining: int | None = None,
        can_retry: bool = False,
    ) -> None:
        super().__init__(message)
        self.restore_id = restore_id
        self.attempt = attempt
        self.retries_remaining = retries_remaining
        self.can_retry = can_retry


class VerificationRetryExhaustedError(ValueError):
    def __init__(self, message: str, restore_id: UUID | None = None) -> None:
        super().__init__(message)
        self.restore_id = restore_id
