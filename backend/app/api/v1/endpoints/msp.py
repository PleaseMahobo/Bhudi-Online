"""Phase 16 — Multi-Tenant MSP API endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.msp import (
    BillingPlanCreate,
    BillingPlanResponse,
    BillingPlanUpdate,
    BrandingResponse,
    BrandingUpdate,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
    TechnicianCreate,
    TechnicianResponse,
    TechnicianUpdate,
    TenantIsolationSummary,
)
from app.services.msp_service import MspService

router = APIRouter(prefix="/msp", tags=["MSP Multi-Tenant"])


@router.post("/organizations", response_model=OrganizationResponse, status_code=201)
def create_organization(payload: OrganizationCreate, db: Session = Depends(get_db)):
    try:
        return MspService(db).create_organization(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    org_type: str | None = None,
    status: str | None = None,
    parent_id: UUID | None = None,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return MspService(db).list_organizations(
        org_type=org_type, status=status, parent_id=parent_id, tenant_id=tenant_id
    )


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
def get_organization(org_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_organization(org_id)
    if not row:
        raise HTTPException(404, "Organization not found")
    return row


@router.patch("/organizations/{org_id}", response_model=OrganizationResponse)
def update_organization(org_id: UUID, payload: OrganizationUpdate, db: Session = Depends(get_db)):
    try:
        row = MspService(db).update_organization(org_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not row:
        raise HTTPException(404, "Organization not found")
    return row


@router.delete("/organizations/{org_id}", status_code=204)
def delete_organization(org_id: UUID, db: Session = Depends(get_db)):
    if not MspService(db).delete_organization(org_id):
        raise HTTPException(404, "Organization not found")


@router.get("/organizations/{org_id}/clients", response_model=list[OrganizationResponse])
def list_client_orgs(org_id: UUID, db: Session = Depends(get_db)):
    return MspService(db).list_client_orgs(org_id)


@router.post("/sites", response_model=SiteResponse, status_code=201)
def create_site(payload: SiteCreate, db: Session = Depends(get_db)):
    try:
        return MspService(db).create_site(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/sites", response_model=list[SiteResponse])
def list_sites(
    organization_id: UUID | None = None,
    tenant_id: UUID | None = None,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    return MspService(db).list_sites(
        organization_id=organization_id, tenant_id=tenant_id, enabled_only=enabled_only
    )


@router.get("/sites/{site_id}", response_model=SiteResponse)
def get_site(site_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_site(site_id)
    if not row:
        raise HTTPException(404, "Site not found")
    return row


@router.patch("/sites/{site_id}", response_model=SiteResponse)
def update_site(site_id: UUID, payload: SiteUpdate, db: Session = Depends(get_db)):
    row = MspService(db).update_site(site_id, payload)
    if not row:
        raise HTTPException(404, "Site not found")
    return row


@router.delete("/sites/{site_id}", status_code=204)
def delete_site(site_id: UUID, db: Session = Depends(get_db)):
    if not MspService(db).delete_site(site_id):
        raise HTTPException(404, "Site not found")


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    try:
        return MspService(db).create_department(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(
    organization_id: UUID | None = None,
    site_id: UUID | None = None,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return MspService(db).list_departments(
        organization_id=organization_id, site_id=site_id, tenant_id=tenant_id
    )


@router.get("/departments/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_department(dept_id)
    if not row:
        raise HTTPException(404, "Department not found")
    return row


@router.patch("/departments/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: UUID, payload: DepartmentUpdate, db: Session = Depends(get_db)):
    row = MspService(db).update_department(dept_id, payload)
    if not row:
        raise HTTPException(404, "Department not found")
    return row


@router.delete("/departments/{dept_id}", status_code=204)
def delete_department(dept_id: UUID, db: Session = Depends(get_db)):
    if not MspService(db).delete_department(dept_id):
        raise HTTPException(404, "Department not found")


@router.post("/contacts", response_model=ContactResponse, status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    try:
        return MspService(db).create_contact(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/contacts", response_model=list[ContactResponse])
def list_contacts(
    organization_id: UUID | None = None,
    tenant_id: UUID | None = None,
    contact_type: str | None = None,
    db: Session = Depends(get_db),
):
    return MspService(db).list_contacts(
        organization_id=organization_id, tenant_id=tenant_id, contact_type=contact_type
    )


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_contact(contact_id)
    if not row:
        raise HTTPException(404, "Contact not found")
    return row


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: UUID, payload: ContactUpdate, db: Session = Depends(get_db)):
    row = MspService(db).update_contact(contact_id, payload)
    if not row:
        raise HTTPException(404, "Contact not found")
    return row


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: UUID, db: Session = Depends(get_db)):
    if not MspService(db).delete_contact(contact_id):
        raise HTTPException(404, "Contact not found")


@router.post("/technicians", response_model=TechnicianResponse, status_code=201)
def create_technician(payload: TechnicianCreate, db: Session = Depends(get_db)):
    try:
        return MspService(db).create_technician(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/technicians", response_model=list[TechnicianResponse])
def list_technicians(
    organization_id: UUID | None = None,
    tenant_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return MspService(db).list_technicians(
        organization_id=organization_id, tenant_id=tenant_id, status=status
    )


@router.get("/technicians/{tech_id}", response_model=TechnicianResponse)
def get_technician(tech_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_technician(tech_id)
    if not row:
        raise HTTPException(404, "Technician not found")
    return row


@router.patch("/technicians/{tech_id}", response_model=TechnicianResponse)
def update_technician(tech_id: UUID, payload: TechnicianUpdate, db: Session = Depends(get_db)):
    row = MspService(db).update_technician(tech_id, payload)
    if not row:
        raise HTTPException(404, "Technician not found")
    return row


@router.delete("/technicians/{tech_id}", status_code=204)
def delete_technician(tech_id: UUID, db: Session = Depends(get_db)):
    if not MspService(db).delete_technician(tech_id):
        raise HTTPException(404, "Technician not found")


@router.get("/technicians/{tech_id}/accessible-tenants")
def technician_accessible_tenants(tech_id: UUID, db: Session = Depends(get_db)):
    ids = MspService(db).accessible_tenant_ids_for_tech(tech_id)
    if not ids and not MspService(db).get_technician(tech_id):
        raise HTTPException(404, "Technician not found")
    return {"technician_id": str(tech_id), "tenant_ids": [str(i) for i in ids]}


@router.get("/tenants/{tenant_id}/branding", response_model=BrandingResponse)
def get_branding(tenant_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_branding(tenant_id)
    if not row:
        raise HTTPException(404, "Branding not configured")
    return row


@router.put("/tenants/{tenant_id}/branding", response_model=BrandingResponse)
def upsert_branding(tenant_id: UUID, payload: BrandingUpdate, db: Session = Depends(get_db)):
    try:
        return MspService(db).upsert_branding(tenant_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/billing/plans/seed", response_model=list[BillingPlanResponse], status_code=201)
def seed_plans(db: Session = Depends(get_db)):
    return MspService(db).seed_default_plans()


@router.post("/billing/plans", response_model=BillingPlanResponse, status_code=201)
def create_plan(payload: BillingPlanCreate, db: Session = Depends(get_db)):
    try:
        return MspService(db).create_plan(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/billing/plans", response_model=list[BillingPlanResponse])
def list_plans(active_only: bool = False, db: Session = Depends(get_db)):
    return MspService(db).list_plans(active_only=active_only)


@router.get("/billing/plans/{plan_id}", response_model=BillingPlanResponse)
def get_plan(plan_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_plan(plan_id)
    if not row:
        raise HTTPException(404, "Plan not found")
    return row


@router.patch("/billing/plans/{plan_id}", response_model=BillingPlanResponse)
def update_plan(plan_id: UUID, payload: BillingPlanUpdate, db: Session = Depends(get_db)):
    row = MspService(db).update_plan(plan_id, payload)
    if not row:
        raise HTTPException(404, "Plan not found")
    return row


@router.delete("/billing/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: UUID, db: Session = Depends(get_db)):
    if not MspService(db).delete_plan(plan_id):
        raise HTTPException(404, "Plan not found")


@router.post("/billing/subscriptions", response_model=SubscriptionResponse, status_code=201)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    try:
        return MspService(db).create_subscription(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/tenants/{tenant_id}/subscription", response_model=SubscriptionResponse)
def get_subscription(tenant_id: UUID, db: Session = Depends(get_db)):
    row = MspService(db).get_subscription(tenant_id)
    if not row:
        raise HTTPException(404, "Subscription not found")
    return row


@router.patch("/tenants/{tenant_id}/subscription", response_model=SubscriptionResponse)
def update_subscription(
    tenant_id: UUID, payload: SubscriptionUpdate, db: Session = Depends(get_db)
):
    row = MspService(db).update_subscription(tenant_id, payload)
    if not row:
        raise HTTPException(404, "Subscription not found")
    return row


@router.get("/tenants/{tenant_id}/isolation", response_model=TenantIsolationSummary)
def isolation_summary(tenant_id: UUID, db: Session = Depends(get_db)):
    return MspService(db).isolation_summary(tenant_id)
