"""Pydantic schemas for Phase 16 — Multi-Tenant MSP."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=128)
    org_type: str = Field("client", pattern="^(msp|client|internal)$")
    status: str = Field("active", pattern="^(active|trial|suspended|churned)$")
    parent_id: UUID | None = None
    tenant_id: UUID | None = None
    legal_name: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    notes: str | None = None
    settings: dict[str, Any] | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    org_type: str | None = None
    status: str | None = None
    parent_id: UUID | None = None
    legal_name: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    notes: str | None = None
    settings: dict[str, Any] | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    parent_id: UUID | None = None
    name: str
    slug: str
    org_type: str
    status: str
    legal_name: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    notes: str | None = None
    settings: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class SiteCreate(BaseModel):
    organization_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    phone: str | None = None
    enabled: bool = True
    meta: dict[str, Any] | None = None


class SiteUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    phone: str | None = None
    enabled: bool | None = None
    meta: dict[str, Any] | None = None


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    organization_id: UUID
    name: str
    code: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    phone: str | None = None
    enabled: bool
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class DepartmentCreate(BaseModel):
    organization_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    site_id: UUID | None = None
    description: str | None = None
    enabled: bool = True


class DepartmentUpdate(BaseModel):
    name: str | None = None
    site_id: UUID | None = None
    description: str | None = None
    enabled: bool | None = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    organization_id: UUID
    site_id: UUID | None = None
    name: str
    description: str | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    organization_id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    title: str | None = None
    contact_type: str = Field("other", pattern="^(primary|billing|technical|executive|other)$")
    is_primary: bool = False
    site_id: UUID | None = None
    department_id: UUID | None = None
    notes: str | None = None
    enabled: bool = True


class ContactUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    title: str | None = None
    contact_type: str | None = None
    is_primary: bool | None = None
    site_id: UUID | None = None
    department_id: UUID | None = None
    notes: str | None = None
    enabled: bool | None = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    organization_id: UUID
    site_id: UUID | None = None
    department_id: UUID | None = None
    first_name: str
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    title: str | None = None
    contact_type: str
    is_primary: bool
    notes: str | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class TechnicianCreate(BaseModel):
    organization_id: UUID
    display_name: str = Field(..., min_length=1, max_length=255)
    user_id: UUID | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    status: str = Field("active", pattern="^(active|inactive|on_leave)$")
    skills: list[str] | None = None
    role_name: str | None = None
    is_msp_admin: bool = False
    assigned_tenant_ids: list[UUID] | None = None
    notes: str | None = None


class TechnicianUpdate(BaseModel):
    display_name: str | None = None
    user_id: UUID | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    status: str | None = None
    skills: list[str] | None = None
    role_name: str | None = None
    is_msp_admin: bool | None = None
    assigned_tenant_ids: list[UUID] | None = None
    notes: str | None = None


class TechnicianResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    organization_id: UUID
    user_id: UUID | None = None
    display_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    status: str
    skills: list[Any] | None = None
    role_name: str | None = None
    is_msp_admin: bool
    assigned_tenant_ids: list[Any] | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class BrandingUpdate(BaseModel):
    portal_name: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    support_email: str | None = None
    support_phone: str | None = None
    custom_css: str | None = None
    login_message: str | None = None
    extra: dict[str, Any] | None = None


class BrandingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    organization_id: UUID
    portal_name: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    support_email: str | None = None
    support_phone: str | None = None
    custom_css: str | None = None
    login_message: str | None = None
    extra: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class BillingPlanCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    interval: str = Field("monthly", pattern="^(monthly|yearly)$")
    price: float = 0
    currency: str = "USD"
    included_devices: int | None = None
    included_users: int | None = None
    features: dict[str, Any] | None = None
    active: bool = True


class BillingPlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    interval: str | None = None
    price: float | None = None
    currency: str | None = None
    included_devices: int | None = None
    included_users: int | None = None
    features: dict[str, Any] | None = None
    active: bool | None = None


class BillingPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None = None
    interval: str
    price: float
    currency: str
    included_devices: int | None = None
    included_users: int | None = None
    features: dict[str, Any] | None = None
    active: bool
    created_at: datetime
    updated_at: datetime


class SubscriptionCreate(BaseModel):
    organization_id: UUID
    plan_id: UUID | None = None
    status: str = Field("trialing", pattern="^(trialing|active|past_due|cancelled|paused)$")
    seats: int | None = None
    device_limit: int | None = None
    trial_ends_at: datetime | None = None
    external_customer_id: str | None = None
    external_subscription_id: str | None = None
    meta: dict[str, Any] | None = None


class SubscriptionUpdate(BaseModel):
    plan_id: UUID | None = None
    status: str | None = None
    seats: int | None = None
    device_limit: int | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    trial_ends_at: datetime | None = None
    cancelled_at: datetime | None = None
    external_customer_id: str | None = None
    external_subscription_id: str | None = None
    meta: dict[str, Any] | None = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    organization_id: UUID
    plan_id: UUID | None = None
    status: str
    seats: int | None = None
    device_limit: int | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    trial_ends_at: datetime | None = None
    cancelled_at: datetime | None = None
    external_customer_id: str | None = None
    external_subscription_id: str | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class TenantIsolationSummary(BaseModel):
    tenant_id: UUID
    organization_id: UUID | None = None
    org_name: str | None = None
    org_type: str | None = None
    sites: int = 0
    departments: int = 0
    contacts: int = 0
    technicians: int = 0
    has_branding: bool = False
    subscription_status: str | None = None


class CustomerWizardSite(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = None
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    phone: str | None = None


class CustomerWizardContact(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None


class CustomerWizardCreate(BaseModel):
    """Create organization + default site + primary contact in one call."""

    name: str = Field(..., min_length=1, max_length=255)
    org_type: str = Field("client", pattern="^(msp|client|internal)$")
    status: str = Field("active", pattern="^(active|trial|suspended|churned)$")
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    notes: str | None = None
    site: CustomerWizardSite
    contact: CustomerWizardContact


class CustomerWizardResponse(BaseModel):
    organization: OrganizationResponse
    site: SiteResponse
    contact: ContactResponse


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = Field(
        "viewer",
        pattern="^(viewer|technician|manager|admin|customer|system_admin)$",
    )
    tenant_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    temporary_password: str | None = Field(
        None,
        description="Optional. If omitted, a secure temporary password is generated.",
    )


class InviteUserResponse(BaseModel):
    user_id: UUID
    email: str
    role: str
    tenant_id: UUID
    temporary_password: str
    message: str
