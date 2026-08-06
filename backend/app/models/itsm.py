from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServiceTicket(Base):
    """
    ITSM ticket: incident | service_request | problem | change | maintenance.

    Links to assets, devices, SOC incidents, and contracts for full
    asset ↔ service-desk integration.
    """

    __tablename__ = "service_tickets"
    __table_args__ = (
        Index("ix_service_tickets_tenant_id", "tenant_id"),
        Index("ix_service_tickets_status", "status"),
        Index("ix_service_tickets_priority", "priority"),
        Index("ix_service_tickets_ticket_type", "ticket_type"),
        Index("ix_service_tickets_number", "number"),
        Index("ix_service_tickets_device_id", "device_id"),
        Index("ix_service_tickets_incident_id", "incident_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )

    # Human-readable ticket number e.g. INC-20260806-A1B2
    number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # incident | service_request | problem | change | maintenance
    ticket_type: Mapped[str] = mapped_column(String(32), nullable=False, default="incident")

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # open | in_progress | on_hold | resolved | closed | cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    # low | medium | high | critical
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    # low | medium | high
    impact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(32), nullable=True)

    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True)

    requester: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignment_group: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Linked operational objects
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    # Optional link to existing SOC incident (string PK in incidents table)
    incident_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True
    )

    # Origin of ticket: manual | asset_lifecycle | warranty | alert | agent
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # SLA placeholders (minutes)
    sla_response_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sla_resolve_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    asset_links = relationship(
        "TicketAssetLink", back_populates="ticket", cascade="all, delete-orphan"
    )
    work_notes = relationship(
        "TicketWorkNote", back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketAssetLink(Base):
    """Many-to-many: service ticket ↔ asset."""

    __tablename__ = "ticket_asset_links"
    __table_args__ = (
        Index("ix_ticket_asset_links_ticket_id", "ticket_id"),
        Index("ix_ticket_asset_links_asset_id", "asset_id"),
        Index(
            "uq_ticket_asset_link",
            "ticket_id",
            "asset_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    # primary | related | impacted
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="primary")
    linked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    ticket = relationship("ServiceTicket", back_populates="asset_links")
    asset = relationship("Asset")


class TicketWorkNote(Base):
    """Chronological work notes / activity on a ticket."""

    __tablename__ = "ticket_work_notes"
    __table_args__ = (Index("ix_ticket_work_notes_ticket_id", "ticket_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )

    ticket = relationship("ServiceTicket", back_populates="work_notes")
