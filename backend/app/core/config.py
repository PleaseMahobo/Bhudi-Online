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

    # =====================================================
    # Refresh Token Security
    # =====================================================

    REFRESH_TOKEN_HASH_KEY: str = os.getenv(
        "REFRESH_TOKEN_HASH_KEY",
        "c3eb91ebc20ec035c43d8ddb7de9b746ed934cff133eaa17a755f1f05e4f8808",
    )

    # =====================================================
    # Password Hashing - Argon2id
    # =====================================================

    ARGON2_TIME_COST: int = int(
        os.getenv(
            "ARGON2_TIME_COST",
            "3",
        )
    )

    ARGON2_MEMORY_COST: int = int(
        os.getenv(
            "ARGON2_MEMORY_COST",
            "65536",
        )
    )

    ARGON2_PARALLELISM: int = int(
        os.getenv(
            "ARGON2_PARALLELISM",
            "4",
        )
    )

    ARGON2_HASH_LENGTH: int = int(
        os.getenv(
            "ARGON2_HASH_LENGTH",
            "32",
        )
    )

    ARGON2_SALT_LENGTH: int = int(
        os.getenv(
            "ARGON2_SALT_LENGTH",
            "16",
        )
    )

    def validate(self):

        required = {
            "DATABASE_URL": self.DATABASE_URL,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
        }

        missing = [
            key
            for key, value in required.items()
            if not value
        ]

        if missing:

            raise RuntimeError(
                f"Missing configuration: {missing}"
            )


settings = Settings()