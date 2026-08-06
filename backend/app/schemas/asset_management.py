from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ---------- Vendor ----------

class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")

    model_config = ConfigDict(populate_by_name=True)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    metadata_json: dict[str, Any] | None = None


class VendorResponse(BaseModel):
    id: UUID
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Asset ----------

class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    asset_tag: str | None = None
    serial_number: str | None = None
    asset_type: str = "hardware"
    category: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    status: str = "in_stock"
    location: str | None = None
    assigned_to: str | None = None
    deployed_at: date | None = None
    retired_at: date | None = None
    warranty_provider: str | None = None
    warranty_start: date | None = None
    warranty_end: date | None = None
    warranty_lookup_ref: str | None = None
    warranty_notes: str | None = None
    purchase_cost: Decimal | None = None
    currency: str = "ZAR"
    purchase_date: date | None = None
    salvage_value: Decimal | None = None
    useful_life_months: int | None = None
    depreciation_method: str = "straight_line"
    tenant_id: UUID | None = None
    device_id: UUID | None = None
    vendor_id: UUID | None = None
    notes: str | None = None
    tags: dict[str, Any] | None = None
    specs: dict[str, Any] | None = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    asset_tag: str | None = None
    serial_number: str | None = None
    asset_type: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    status: str | None = None
    location: str | None = None
    assigned_to: str | None = None
    deployed_at: date | None = None
    retired_at: date | None = None
    warranty_provider: str | None = None
    warranty_start: date | None = None
    warranty_end: date | None = None
    warranty_lookup_ref: str | None = None
    warranty_notes: str | None = None
    purchase_cost: Decimal | None = None
    currency: str | None = None
    purchase_date: date | None = None
    salvage_value: Decimal | None = None
    useful_life_months: int | None = None
    depreciation_method: str | None = None
    tenant_id: UUID | None = None
    device_id: UUID | None = None
    vendor_id: UUID | None = None
    notes: str | None = None
    tags: dict[str, Any] | None = None
    specs: dict[str, Any] | None = None


class AssetResponse(AssetBase):
    id: UUID
    current_book_value: Decimal | None = None
    qr_code: str | None = None
    qr_payload: str | None = None
    warranty_active: bool | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarrantyLookupResponse(BaseModel):
    asset_id: UUID
    serial_number: str | None
    warranty_provider: str | None
    warranty_start: date | None
    warranty_end: date | None
    warranty_lookup_ref: str | None
    warranty_active: bool
    days_remaining: int | None
    notes: str | None


class DepreciationResponse(BaseModel):
    asset_id: UUID
    method: str
    purchase_cost: Decimal | None
    salvage_value: Decimal | None
    useful_life_months: int | None
    purchase_date: date | None
    months_elapsed: int | None
    current_book_value: Decimal | None
    accumulated_depreciation: Decimal | None


class QrCodeResponse(BaseModel):
    asset_id: UUID
    qr_code: str
    qr_payload: str


# ---------- Software ----------

class SoftwareItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str | None = None
    publisher: str | None = None
    install_path: str | None = None
    install_date: date | None = None
    is_managed: bool = False
    license_key_hint: str | None = None
    asset_id: UUID | None = None
    device_id: UUID | None = None
    tenant_id: UUID | None = None
    raw: dict[str, Any] | None = None


class SoftwareItemCreate(SoftwareItemBase):
    pass


class SoftwareItemUpdate(BaseModel):
    name: str | None = None
    version: str | None = None
    publisher: str | None = None
    install_path: str | None = None
    install_date: date | None = None
    is_managed: bool | None = None
    license_key_hint: str | None = None
    raw: dict[str, Any] | None = None


class SoftwareItemResponse(SoftwareItemBase):
    id: UUID
    discovered_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- License ----------

class LicenseBase(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=255)
    license_type: str = "perpetual"
    seats_total: int = Field(default=1, ge=1)
    seats_used: int = Field(default=0, ge=0)
    license_key_encrypted: str | None = None
    purchase_date: date | None = None
    expiry_date: date | None = None
    cost: Decimal | None = None
    currency: str = "ZAR"
    notes: str | None = None
    is_active: bool = True
    tenant_id: UUID | None = None
    vendor_id: UUID | None = None


class LicenseCreate(LicenseBase):
    pass


class LicenseUpdate(BaseModel):
    product_name: str | None = None
    license_type: str | None = None
    seats_total: int | None = Field(None, ge=1)
    seats_used: int | None = Field(None, ge=0)
    license_key_encrypted: str | None = None
    purchase_date: date | None = None
    expiry_date: date | None = None
    cost: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    vendor_id: UUID | None = None


class LicenseResponse(LicenseBase):
    id: UUID
    seats_available: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LicenseAssignmentCreate(BaseModel):
    license_id: UUID
    asset_id: UUID | None = None
    assigned_to: str | None = None
    notes: str | None = None


class LicenseAssignmentResponse(BaseModel):
    id: UUID
    license_id: UUID
    asset_id: UUID | None
    assigned_to: str | None
    assigned_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


# ---------- Contract ----------

class ContractBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contract_number: str | None = None
    contract_type: str = "support"
    status: str = "active"
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    auto_renew: bool = False
    value: Decimal | None = None
    currency: str = "ZAR"
    terms: str | None = None
    document_url: str | None = None
    notes: str | None = None
    tenant_id: UUID | None = None
    vendor_id: UUID | None = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    name: str | None = None
    contract_number: str | None = None
    contract_type: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    auto_renew: bool | None = None
    value: Decimal | None = None
    currency: str | None = None
    terms: str | None = None
    document_url: str | None = None
    notes: str | None = None
    vendor_id: UUID | None = None


class ContractResponse(ContractBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Purchase ----------

class PurchaseBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=512)
    po_number: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    currency: str = "ZAR"
    purchase_date: date | None = None
    received_date: date | None = None
    status: str = "ordered"
    invoice_ref: str | None = None
    notes: str | None = None
    tenant_id: UUID | None = None
    vendor_id: UUID | None = None
    asset_id: UUID | None = None


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseUpdate(BaseModel):
    description: str | None = None
    po_number: str | None = None
    quantity: int | None = Field(None, ge=1)
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    currency: str | None = None
    purchase_date: date | None = None
    received_date: date | None = None
    status: str | None = None
    invoice_ref: str | None = None
    notes: str | None = None
    vendor_id: UUID | None = None
    asset_id: UUID | None = None


class PurchaseResponse(PurchaseBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Lifecycle ----------

class LifecycleEventResponse(BaseModel):
    id: UUID
    asset_id: UUID
    event_type: str
    from_status: str | None
    to_status: str | None
    actor: str | None
    detail: str | None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatusChangeRequest(BaseModel):
    status: str
    actor: str | None = None
    detail: str | None = None
