from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
    )

    framework: Mapped[str | None] = mapped_column(Text)

    generated_by: Mapped[str | None] = mapped_column(Text)

    report_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP,
        server_default=text("now()"),
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="compliance_reports",
    )