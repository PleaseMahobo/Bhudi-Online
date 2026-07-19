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