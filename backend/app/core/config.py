from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


class Settings:

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "",
    )

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "",
    )

    JWT_ALGORITHM: str = os.getenv(
        "JWT_ALGORITHM",
        "HS256",
    )

    JWT_ACCESS_EXPIRE_MINUTES: int = int(
        os.getenv(
            "JWT_ACCESS_EXPIRE_MINUTES",
            "15",
        )
    )

    JWT_REFRESH_EXPIRE_DAYS: int = int(
        os.getenv(
            "JWT_REFRESH_EXPIRE_DAYS",
            "30",
        )
    )

    HEARTBEAT_TIMEOUT_SECONDS: int = int(
        os.getenv(
            "HEARTBEAT_TIMEOUT_SECONDS",
            "90",
        )
    )

    OFFLINE_SCAN_INTERVAL: int = int(
        os.getenv(
            "OFFLINE_SCAN_INTERVAL",
            "30",
        )
    )

    REFRESH_TOKEN_HASH_KEY: str = os.getenv(
        "REFRESH_TOKEN_HASH_KEY",
        "c3eb91ebc20ec035c43d8ddb7de9b746ed934cff133eaa17a755f1f05e4f8808",
    )

    ARGON2_TIME_COST: int = int(os.getenv("ARGON2_TIME_COST", "3"))
    ARGON2_MEMORY_COST: int = int(os.getenv("ARGON2_MEMORY_COST", "65536"))
    ARGON2_PARALLELISM: int = int(os.getenv("ARGON2_PARALLELISM", "4"))
    ARGON2_HASH_LENGTH: int = int(os.getenv("ARGON2_HASH_LENGTH", "32"))
    ARGON2_SALT_LENGTH: int = int(os.getenv("ARGON2_SALT_LENGTH", "16"))

    # Resend (preferred email delivery — HTTP API, works well on Railway)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "")
    RESEND_FROM_NAME: str = os.getenv("RESEND_FROM_NAME", "Bhudi RMM")
    RESEND_ENABLED: bool = os.getenv("RESEND_ENABLED", "true").lower() in (
        "1", "true", "yes", "on",
    )

    # SMTP / email delivery (fallback if Resend is not configured)
    SMTP_ENABLED: bool = os.getenv("SMTP_ENABLED", "false").lower() in (
        "1", "true", "yes", "on",
    )
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in (
        "1", "true", "yes", "on",
    )
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() in (
        "1", "true", "yes", "on",
    )
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Bhudi RMM")
    SMTP_TIMEOUT: int = int(os.getenv("SMTP_TIMEOUT", "30"))
    SMTP_MAX_RETRIES: int = int(os.getenv("SMTP_MAX_RETRIES", "3"))
    SMTP_RETRY_BASE_DELAY: float = float(os.getenv("SMTP_RETRY_BASE_DELAY", "1.0"))
    SMTP_RETRY_MAX_DELAY: float = float(os.getenv("SMTP_RETRY_MAX_DELAY", "30.0"))

    # Password reset links
    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000",
    ).rstrip("/")
    PASSWORD_RESET_SECRET: str = os.getenv(
        "PASSWORD_RESET_SECRET",
        "",
    )
    PASSWORD_RESET_EXPIRE_MINUTES: int = int(
        os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "60")
    )
    PASSWORD_RESET_ISSUER: str = os.getenv(
        "PASSWORD_RESET_ISSUER",
        "bhudi-api",
    )
    PASSWORD_RESET_AUDIENCE: str = os.getenv(
        "PASSWORD_RESET_AUDIENCE",
        "bhudi-password-reset",
    )

    # Stripe billing / webhooks
    STRIPE_ENABLED: bool = os.getenv("STRIPE_ENABLED", "false").lower() in (
        "1", "true", "yes", "on",
    )
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_WEBHOOK_TOLERANCE: int = int(os.getenv("STRIPE_WEBHOOK_TOLERANCE", "300"))
    STRIPE_STORE_PAYLOAD: bool = os.getenv("STRIPE_STORE_PAYLOAD", "true").lower() in (
        "1", "true", "yes", "on",
    )

    # OpenTelemetry tracing
    OTEL_ENABLED: bool = os.getenv("OTEL_ENABLED", "false").lower() in (
        "1", "true", "yes", "on",
    ) or bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "bhudi-api")
    OTEL_SERVICE_VERSION: str = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    OTEL_ENVIRONMENT: str = os.getenv(
        "OTEL_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")
    )
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    OTEL_EXPORTER_OTLP_PROTOCOL: str = os.getenv(
        "OTEL_EXPORTER_OTLP_PROTOCOL", "grpc"
    )
    OTEL_TRACES_SAMPLER: str = os.getenv(
        "OTEL_TRACES_SAMPLER", "parentbased_always_on"
    )
    OTEL_TRACES_SAMPLER_ARG: float = float(
        os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0")
    )
    OTEL_CONSOLE_EXPORTER: bool = os.getenv("OTEL_CONSOLE_EXPORTER", "false").lower() in (
        "1", "true", "yes", "on",
    )

    def validate(self):
        required = {
            "DATABASE_URL": self.DATABASE_URL,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing configuration: {missing}")


settings = Settings()
