from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


PSA_PROVIDERS = (
    "autotask",
    "halopsa",
    "connectwise",
    "freshservice",
    "jira",
    "zendesk",
    "servicenow",
)


class PSAConnection(Base):
    """Tenant-scoped PSA / helpdesk connector configuration."""

    __tablename__ = "psa_connections"
    __table_args__ = (
        Index("ix_psa_connections_tenant_id", "tenant_id"),
        Index("ix_psa_connections_provider_key", "provider_key"),
        Index("ix_psa_connections_enabled", "enabled"),
        Index(
            "uq_psa_connection_tenant_provider",
            "tenant_id",
            "provider_key",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # base_url, auth fields (api_key, username, password, client_id, ...), mapping overrides
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # never | ok | error
    last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ticket_links = relationship(
        "PSATicketLink", back_populates="connection", cascade="all, delete-orphan"
    )
    sync_events = relationship(
        "PSASyncEvent", back_populates="connection", cascade="all, delete-orphan"
    )


class PSATicketLink(Base):
    """Maps an internal ServiceTicket to an external PSA ticket."""

    __tablename__ = "psa_ticket_links"
    __table_args__ = (
        Index("ix_psa_ticket_links_connection_id", "connection_id"),
        Index("ix_psa_ticket_links_ticket_id", "ticket_id"),
        Index("ix_psa_ticket_links_external_id", "external_id"),
        Index(
            "uq_psa_ticket_link_connection_ticket",
            "connection_id",
            "ticket_id",
            unique=True,
        ),
        Index(
            "uq_psa_ticket_link_connection_external",
            "connection_id",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("psa_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_tickets.id", ondelete="CASCADE"),
        nullable=False,
    )

    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    external_status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # outbound | inbound | bidirectional
    direction: Mapped[str] = mapped_column(String(32), nullable=False, default="outbound")
    sync_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="linked"
    )  # linked | pending | error | unlinked
    last_synced_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    connection = relationship("PSAConnection", back_populates="ticket_links")
    ticket = relationship("ServiceTicket")


class PSASyncEvent(Base):
    """Idempotent log of inbound webhooks and outbound API operations."""

    __tablename__ = "psa_sync_events"
    __table_args__ = (
        Index("ix_psa_sync_events_connection_id", "connection_id"),
        Index("ix_psa_sync_events_event_type", "event_type"),
        Index("ix_psa_sync_events_status", "status"),
        Index("ix_psa_sync_events_external_event_id", "external_event_id"),
        Index(
            "uq_psa_sync_events_connection_external",
            "connection_id",
            "external_event_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("psa_connections.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ticket.created | ticket.updated | ticket.closed | test | push | pull
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="inbound")
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_ticket_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # received | processed | ignored | error
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    action: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    connection = relationship("PSAConnection", back_populates="sync_events")
