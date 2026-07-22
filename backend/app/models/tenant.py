from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .agent import Agent
    from .alert import Alert
    from .compliance_report import ComplianceReport
    from .device import Device
    from .device_event import DeviceEvent
    from .device_metric import DeviceMetric
    from .profile import Profile
    from .user import User


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
    )

    #
    # Relationships
    #

    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="tenant",
    )

    agents: Mapped[list["Agent"]] = relationship(
        "Agent",
        back_populates="tenant",
    )

    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="tenant",
    )

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
    )

    profiles: Mapped[list["Profile"]] = relationship(
        "Profile",
        back_populates="tenant",
    )

    compliance_reports: Mapped[list["ComplianceReport"]] = relationship(
        "ComplianceReport",
        back_populates="tenant",
    )

    device_events: Mapped[list["DeviceEvent"]] = relationship(
        "DeviceEvent",
        back_populates="tenant",
    )

    device_metrics: Mapped[list["DeviceMetric"]] = relationship(
        "DeviceMetric",
        back_populates="tenant",
    )

    def __repr__(self) -> str:
        return (
            f"<Tenant("
            f"id={self.id}, "
            f"name={self.name!r}"
            f")>"
        )