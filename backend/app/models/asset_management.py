from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Vendor(Base):
    """Supplier / manufacturer / service provider."""

    __tablename__ = "vendors"
    __table_args__ = (Index("ix_vendors_name", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    assets = relationship("Asset", back_populates="vendor")
    contracts = relationship("Contract", back_populates="vendor")
    purchases = relationship("Purchase", back_populates="vendor")
    licenses = relationship("License", back_populates="vendor")


class Asset(Base):
    """Hardware (and linked) asset inventory record."""

    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_tenant_id", "tenant_id"),
        Index("ix_assets_device_id", "device_id"),
        Index("ix_assets_status", "status"),
        Index("ix_assets_asset_tag", "asset_tag"),
        Index("ix_assets_serial_number", "serial_number"),
        Index("ix_assets_qr_code", "qr_code"),
        Index("ix_assets_warranty_end", "warranty_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_tag: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="hardware"
    )  # hardware | peripheral | network | other
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Lifecycle
    # ordered | received | in_stock | deployed | in_repair | retired | disposed
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="in_stock")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deployed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    retired_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Warranty
    warranty_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warranty_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_lookup_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # external ticket / OEM ref
    warranty_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Financial / depreciation
    purchase_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="ZAR")
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salvage_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    useful_life_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # straight_line | declining_balance | none
    depreciation_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="straight_line"
    )
    current_book_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # QR
    qr_code: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    qr_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    specs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    vendor = relationship("Vendor", back_populates="assets")
    software_items = relationship(
        "SoftwareInventoryItem", back_populates="asset", cascade="all, delete-orphan"
    )
    lifecycle_events = relationship(
        "AssetLifecycleEvent", back_populates="asset", cascade="all, delete-orphan"
    )
    license_assignments = relationship(
        "LicenseAssignment", back_populates="asset", cascade="all, delete-orphan"
    )


class SoftwareInventoryItem(Base):
    """Installed / discovered software inventory."""

    __tablename__ = "software_inventory"
    __table_args__ = (
        Index("ix_software_inventory_asset_id", "asset_id"),
        Index("ix_software_inventory_device_id", "device_id"),
        Index("ix_software_inventory_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    install_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    install_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    license_key_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    discovered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    asset = relationship("Asset", back_populates="software_items")


class License(Base):
    """Software / SaaS license pool."""

    __tablename__ = "licenses"
    __table_args__ = (
        Index("ix_licenses_tenant_id", "tenant_id"),
        Index("ix_licenses_product_name", "product_name"),
        Index("ix_licenses_expiry_date", "expiry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )

    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="perpetual"
    )  # perpetual | subscription | concurrent | site
    seats_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    seats_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    license_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="ZAR")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    vendor = relationship("Vendor", back_populates="licenses")
    assignments = relationship(
        "LicenseAssignment", back_populates="license", cascade="all, delete-orphan"
    )


class LicenseAssignment(Base):
    """Seat assignment of a license to an asset or user."""

    __tablename__ = "license_assignments"
    __table_args__ = (
        Index("ix_license_assignments_license_id", "license_id"),
        Index("ix_license_assignments_asset_id", "asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    license_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    license = relationship("License", back_populates="assignments")
    asset = relationship("Asset", back_populates="license_assignments")


class Contract(Base):
    """Vendor / support / SLA contracts."""

    __tablename__ = "contracts"
    __table_args__ = (
        Index("ix_contracts_tenant_id", "tenant_id"),
        Index("ix_contracts_end_date", "end_date"),
        Index("ix_contracts_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contract_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="support"
    )  # support | lease | msa | nda | other
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="active"
    )  # draft | active | expired | terminated
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="ZAR")
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    vendor = relationship("Vendor", back_populates="contracts")


class Purchase(Base):
    """Purchase order / acquisition record."""

    __tablename__ = "purchases"
    __table_args__ = (
        Index("ix_purchases_tenant_id", "tenant_id"),
        Index("ix_purchases_purchase_date", "purchase_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    po_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="ZAR")
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="ordered"
    )  # ordered | received | cancelled | returned
    invoice_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    vendor = relationship("Vendor", back_populates="purchases")


class AssetLifecycleEvent(Base):
    """Audit trail of lifecycle transitions."""

    __tablename__ = "asset_lifecycle_events"
    __table_args__ = (
        Index("ix_asset_lifecycle_events_asset_id", "asset_id"),
        Index("ix_asset_lifecycle_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # created | status_change | assigned | warranty_updated | depreciated | qr_generated | note
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=_utcnow, nullable=False
    )

    asset = relationship("Asset", back_populates="lifecycle_events")
