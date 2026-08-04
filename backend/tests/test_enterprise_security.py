from __future__ import annotations

from datetime import datetime, timezone

from app.core.security import hash_password
from app.services.auth_service import AuthService


class DummyUser:
    def __init__(self) -> None:
        self.id = "user-1"
        self.email = "demo@example.com"
        self.first_name = "Demo"
        self.last_name = "User"
        self.role = "user"
        self.active = True
        self.locked_until = None
        self.failed_login_attempts = 0
        self.password_hash = "hash"
        self.password_changed_at = None
        self.last_login_at = None
        self.password_history = []


class DummyRefreshToken:
    def __init__(self) -> None:
        self.ip_address = "203.0.113.10"
        self.user_agent = "Mozilla/5.0"
        self.device_name = "laptop"
        self.risk_score = 20
        self.token_family = "family-1"


def test_password_history_and_risk_score_helpers() -> None:
    service = AuthService.__new__(AuthService)

    user = DummyUser()
    history = ["OldPassword123!", "OlderPassword456!"]
    user.password_history = history

    assert service._is_password_reused(user, "OldPassword123!") is True
    assert service._is_password_reused(user, "NewPassword789!") is False

    risk = service._assess_login_risk(
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
        device_name="laptop",
        previous_login_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        current_login_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        password_history=history,
    )

    assert risk >= 0
    assert risk <= 100


def test_password_reuse_detection_uses_stored_hashes() -> None:
    service = AuthService.__new__(AuthService)
    user = DummyUser()
    user.password_history = [hash_password("OldPassword123!")]

    assert service._is_password_reused(user, "OldPassword123!") is True
    assert service._is_password_reused(user, "NewPassword789!") is False


def test_session_context_mismatch_is_detected() -> None:
    service = AuthService.__new__(AuthService)
    token = DummyRefreshToken()

    assert service._is_session_anomalous(
        token,
        ip_address="198.51.100.20",
        user_agent="Mozilla/5.0",
        device_name="laptop",
    ) is True
    assert service._is_session_anomalous(
        token,
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
        device_name="laptop",
    ) is False
