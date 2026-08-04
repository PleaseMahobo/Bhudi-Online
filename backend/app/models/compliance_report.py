from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .tenant import Tenant


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    framework: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    generated_by: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    report_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    #
    # Relationships
    #

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="compliance_reports",
    )

    def __repr__(self) -> str:
        return (
            f"<ComplianceReport("
            f"id={self.id}, "
            f"framework={self.framework!r}"
            f")>"
        )