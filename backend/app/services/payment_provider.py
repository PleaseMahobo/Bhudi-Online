"""Provider-agnostic payment gateway contracts for Bhudi billing.

Checkout and subscription ownership remain provider-neutral. Concrete gateways
are selected by provider key and can be added without changing tenant billing
models or entitlement logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


SUPPORTED_PROVIDERS = frozenset({"stripe", "paypal", "pioneer"})


@dataclass(frozen=True)
class PaymentCheckout:
    provider: str
    checkout_url: str | None
    session_id: str | None
    external_customer_id: str | None = None
    external_subscription_id: str | None = None
    raw: dict[str, Any] | None = None


class PaymentProvider(Protocol):
    """Contract every payment gateway adapter must implement."""

    name: str

    def create_subscription_checkout(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        plan_code: str,
        email: str | None,
        customer_name: str | None,
        success_url: str,
        cancel_url: str,
        existing_customer_id: str | None = None,
    ) -> PaymentCheckout:
        ...


class PaymentProviderUnavailable(RuntimeError):
    """Raised when a requested provider is not configured for live use."""


def validate_provider(provider: str) -> str:
    value = (provider or "stripe").strip().lower()
    if value not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported payment provider: {value}")
    return value


def provider_status() -> dict[str, dict[str, Any]]:
    """Stable provider registry for the UI/API; adapters advertise readiness separately."""
    return {
        "stripe": {"enabled": True, "direct": True, "methods": ["card", "paypal"]},
        "paypal": {"enabled": False, "direct": True, "methods": ["paypal"]},
        "pioneer": {"enabled": False, "direct": True, "methods": ["card", "bank"]},
    }
