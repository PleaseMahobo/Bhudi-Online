from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .agent_command import AgentCommand
    from .command import Command
    from .device import Device
    from .tenant import Tenant


class Agent(Base):
    __tablename__ = "agents"

    #
    # Identity
    #

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    hostname: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    device_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    machine_guid: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        unique=True,
        index=True,
    )

    agent_version: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #
    # Platform
    #

    platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    architecture: Mapped[str | None] = mapped_column(Text, nullable=True)
    operating_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    os_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    #
    # Hardware
    #

    manufacturer: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    serial_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    bios_serial: Mapped[str | None] = mapped_column(Text, nullable=True)

    cpu_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)

    memory_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_total_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    #
    # Network
    #

    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    ipv4_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    ipv6_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    mac_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    fqdn: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)

    #
    # Authentication
    #

    api_key_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    enrollment_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    registration_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
    )

    approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    trusted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    #
    # Heartbeat
    #

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="offline",
        index=True,
    )

    registered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    last_seen: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    last_heartbeat: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    heartbeat_interval: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="30",
    )

    poll_interval: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="30",
    )

    #
    # Security
    #

    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    certificate_thumbprint: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tamper_protection: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    #
    # Management
    #

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    auto_update: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    command_timeout: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="300",
    )

    restart_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    #
    # Diagnostics
    #

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    last_error_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    #
    # Multi-tenancy
    #

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )

    #
    # Relationships
    #

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="agents",
    )

    commands: Mapped[list["Command"]] = relationship(
        "Command",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    queued_commands: Mapped[list["AgentCommand"]] = relationship(
        "AgentCommand",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="agent",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )

#
# Agent Identity
#

agent_uuid: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    nullable=False,
    unique=True,
    default=uuid.uuid4,
    index=True,
)

agent_version: Mapped[str] = mapped_column(
    Text,
    nullable=False,
)

agent_build: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

update_channel: Mapped[str] = mapped_column(
    Text,
    nullable=False,
    server_default="stable",
)

#
# Enrollment
#

registration_state: Mapped[str] = mapped_column(
    Text,
    nullable=False,
    server_default="pending",
    index=True,
)

enrollment_secret_hash: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

enrolled_at: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
)

approved_by: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    nullable=True,
)

approved_at: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
)

#
# Authentication
#

public_key: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

certificate_thumbprint: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

trust_level: Mapped[str] = mapped_column(
    Text,
    nullable=False,
    server_default="trusted",
)

secret_version: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    server_default="1",
)

#
# Connectivity
#

heartbeat_interval: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    server_default="30",
)

poll_interval: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    server_default="30",
)

last_heartbeat: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
    index=True,
)

last_checkin: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
)

last_ip_address: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

last_logged_on_user: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

#
# Health
#

status: Mapped[str] = mapped_column(
    Text,
    nullable=False,
    server_default="offline",
    index=True,
)

health_score: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    server_default="100",
)

restart_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    server_default="0",
)

last_error: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

last_error_at: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
)

#
# Security
#

tamper_protection: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    server_default="false",
)

quarantined: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    server_default="false",
)

revoked: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    server_default="false",
)

revoked_at: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
)

revocation_reason: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

#
# Updates
#

auto_update: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    server_default="true",
)

update_available: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    server_default="false",
)

target_version: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)

last_update: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=True,
)

#
# Audit
#

created_at: Mapped[datetime] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=False,
    server_default=func.now(),
)

updated_at: Mapped[datetime] = mapped_column(
    TIMESTAMP(timezone=True),
    nullable=False,
    server_default=func.now(),
    onupdate=func.now(),
)