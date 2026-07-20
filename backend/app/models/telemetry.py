from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Double, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    agent_id: Mapped[str | None] = mapped_column(Text)

    cpu_usage: Mapped[float | None] = mapped_column(Double)

    memory_usage: Mapped[float | None] = mapped_column(Double)

    disk_usage: Mapped[float | None] = mapped_column(Double)

    uptime: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )