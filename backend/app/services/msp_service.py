"""Phase 16 — Multi-Tenant MSP service (CRUD + isolation helpers)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.msp import (
    BillingPlan,
    Contact,
    Department,
    Organization,
    Site,
    Technician,
    TenantBranding,
    TenantSubscription,
)
from app.models.tenant import Tenant
from app.schemas.msp import (
    BillingPlanCreate,
    BillingPlanUpdate,
    BrandingUpdate,
    ContactCreate,
    ContactUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    OrganizationCreate,
    OrganizationUpdate,
    SiteCreate,
    SiteUpdate,
    SubscriptionCreate,
    SubscriptionUpdate,
    TechnicianCreate,
    TechnicianUpdate,
    TenantIsolationSummary,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (s or "org")[:120]


class MspService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ----- Isolation ------------------------------------------------------

    def assert_tenant_access(
        self, tenant_id: UUID, allowed: set[UUID] | list[UUID] | None
    ) -> None:
        """Raise if tenant_id is not in the caller's allowed set (when provided)."""
        if allowed is None:
            return
        allowed_set = set(allowed)
        if tenant_id not in allowed_set:
            raise PermissionError(f"Tenant {tenant_id} is outside isolation scope")

    def isolation_summary(self, tenant_id: UUID) -> TenantIsolationSummary:
        org = (
            self.db.query(Organization)
            .filter(Organization.tenant_id == tenant_id)
            .first()
        )
        sites = self.db.query(Site).filter(Site.tenant_id == tenant_id).count()
        depts = (
            self.db.query(Department)
            .filter(Department.tenant_id == tenant_id)
            .count()
        )
        contacts = (
            self.db.query(Contact).filter(Contact.tenant_id == tenant_id).count()
        )
        techs = (
            self.db.query(Technician)
            .filter(Technician.tenant_id == tenant_id)
            .count()
        )
        branding = (
            self.db.query(TenantBranding)
            .filter(TenantBranding.tenant_id == tenant_id)
            .first()
        )
        sub = (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.tenant_id == tenant_id)
            .first()
        )
        return TenantIsolationSummary(
            tenant_id=tenant_id,
            organization_id=org.id if org else None,
            org_name=org.name if org else None,
            org_type=org.org_type if org else None,
            sites=sites,
            departments=depts,
            contacts=contacts,
            technicians=techs,
            has_branding=branding is not None,
            subscription_status=sub.status if sub else None,
        )

    def accessible_tenant_ids_for_tech(self, technician_id: UUID) -> list[UUID]:
        tech = self.get_technician(technician_id)
        if not tech:
            return []
        ids = [tech.tenant_id]
        for raw in tech.assigned_tenant_ids or []:
            try:
                ids.append(UUID(str(raw)))
            except Exception:
                continue
        seen: set[UUID] = set()
        out: list[UUID] = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    # ----- Organizations --------------------------------------------------

    def create_organization(self, payload: OrganizationCreate) -> Organization:
        tenant_id = payload.tenant_id
        if tenant_id is None:
            tenant = Tenant(name=payload.name)
            self.db.add(tenant)
            self.db.flush()
            tenant_id = tenant.id
        else:
            existing = (
                self.db.query(Organization)
                .filter(Organization.tenant_id == tenant_id)
                .first()
            )
            if existing:
                raise ValueError("Organization already exists for this tenant")

        slug = payload.slug or _slugify(payload.name)
        base = slug
        n = 1
        while self.db.query(Organization).filter(Organization.slug == slug).first():
            n += 1
            slug = f"{base}-{n}"

        row = Organization(
            tenant_id=tenant_id,
            parent_id=payload.parent_id,
            name=payload.name,
            slug=slug,
            org_type=payload.org_type,
            status=payload.status,
            legal_name=payload.legal_name,
            website=payload.website,
            phone=payload.phone,
            email=payload.email,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            postal_code=payload.postal_code,
            country=payload.country,
            timezone=payload.timezone,
            notes=payload.notes,
            settings=payload.settings,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_organizations(
        self,
        *,
        org_type: str | None = None,
        status: str | None = None,
        parent_id: UUID | None = None,
        tenant_id: UUID | None = None,
    ) -> list[Organization]:
        q = self.db.query(Organization)
        if org_type:
            q = q.filter(Organization.org_type == org_type)
        if status:
            q = q.filter(Organization.status == status)
        if parent_id is not None:
            q = q.filter(Organization.parent_id == parent_id)
        if tenant_id is not None:
            q = q.filter(Organization.tenant_id == tenant_id)
        return q.order_by(Organization.name).all()

    def get_organization(self, org_id: UUID) -> Organization | None:
        return (
            self.db.query(Organization).filter(Organization.id == org_id).first()
        )

    def get_organization_by_tenant(self, tenant_id: UUID) -> Organization | None:
        return (
            self.db.query(Organization)
            .filter(Organization.tenant_id == tenant_id)
            .first()
        )

    def update_organization(
        self, org_id: UUID, payload: OrganizationUpdate
    ) -> Organization | None:
        row = self.get_organization(org_id)
        if not row:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "slug" in data and data["slug"]:
            clash = (
                self.db.query(Organization)
                .filter(
                    Organization.slug == data["slug"],
                    Organization.id != org_id,
                )
                .first()
            )
            if clash:
                raise ValueError("Slug already in use")
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_organization(self, org_id: UUID) -> bool:
        row = self.get_organization(org_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def list_client_orgs(self, msp_org_id: UUID) -> list[Organization]:
        """Clients whose parent is the given MSP organization."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.parent_id == msp_org_id,
                Organization.org_type == "client",
            )
            .order_by(Organization.name)
            .all()
        )

    # ----- Sites ----------------------------------------------------------

    def create_site(self, payload: SiteCreate) -> Site:
        org = self.get_organization(payload.organization_id)
        if not org:
            raise ValueError("Organization not found")
        row = Site(
            tenant_id=org.tenant_id,
            organization_id=org.id,
            name=payload.name,
            code=payload.code,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            postal_code=payload.postal_code,
            country=payload.country,
            timezone=payload.timezone,
            phone=payload.phone,
            enabled=payload.enabled,
            meta=payload.meta,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_sites(
        self,
        *,
        organization_id: UUID | None = None,
        tenant_id: UUID | None = None,
        enabled_only: bool = False,
    ) -> list[Site]:
        q = self.db.query(Site)
        if organization_id:
            q = q.filter(Site.organization_id == organization_id)
        if tenant_id:
            q = q.filter(Site.tenant_id == tenant_id)
        if enabled_only:
            q = q.filter(Site.enabled.is_(True))
        return q.order_by(Site.name).all()

    def get_site(self, site_id: UUID) -> Site | None:
        return self.db.query(Site).filter(Site.id == site_id).first()

    def update_site(self, site_id: UUID, payload: SiteUpdate) -> Site | None:
        row = self.get_site(site_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_site(self, site_id: UUID) -> bool:
        row = self.get_site(site_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ----- Departments ----------------------------------------------------

    def create_department(self, payload: DepartmentCreate) -> Department:
        org = self.get_organization(payload.organization_id)
        if not org:
            raise ValueError("Organization not found")
        if payload.site_id:
            site = self.get_site(payload.site_id)
            if not site or site.organization_id != org.id:
                raise ValueError("Site not found in organization")
        row = Department(
            tenant_id=org.tenant_id,
            organization_id=org.id,
            site_id=payload.site_id,
            name=payload.name,
            description=payload.description,
            enabled=payload.enabled,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_departments(
        self,
        *,
        organization_id: UUID | None = None,
        site_id: UUID | None = None,
        tenant_id: UUID | None = None,
    ) -> list[Department]:
        q = self.db.query(Department)
        if organization_id:
            q = q.filter(Department.organization_id == organization_id)
        if site_id:
            q = q.filter(Department.site_id == site_id)
        if tenant_id:
            q = q.filter(Department.tenant_id == tenant_id)
        return q.order_by(Department.name).all()

    def get_department(self, dept_id: UUID) -> Department | None:
        return self.db.query(Department).filter(Department.id == dept_id).first()

    def update_department(
        self, dept_id: UUID, payload: DepartmentUpdate
    ) -> Department | None:
        row = self.get_department(dept_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_department(self, dept_id: UUID) -> bool:
        row = self.get_department(dept_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ----- Contacts -------------------------------------------------------

    def create_contact(self, payload: ContactCreate) -> Contact:
        org = self.get_organization(payload.organization_id)
        if not org:
            raise ValueError("Organization not found")
        row = Contact(
            tenant_id=org.tenant_id,
            organization_id=org.id,
            site_id=payload.site_id,
            department_id=payload.department_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            mobile=payload.mobile,
            title=payload.title,
            contact_type=payload.contact_type,
            is_primary=payload.is_primary,
            notes=payload.notes,
            enabled=payload.enabled,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_contacts(
        self,
        *,
        organization_id: UUID | None = None,
        tenant_id: UUID | None = None,
        contact_type: str | None = None,
    ) -> list[Contact]:
        q = self.db.query(Contact)
        if organization_id:
            q = q.filter(Contact.organization_id == organization_id)
        if tenant_id:
            q = q.filter(Contact.tenant_id == tenant_id)
        if contact_type:
            q = q.filter(Contact.contact_type == contact_type)
        return q.order_by(Contact.last_name, Contact.first_name).all()

    def get_contact(self, contact_id: UUID) -> Contact | None:
        return self.db.query(Contact).filter(Contact.id == contact_id).first()

    def update_contact(
        self, contact_id: UUID, payload: ContactUpdate
    ) -> Contact | None:
        row = self.get_contact(contact_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_contact(self, contact_id: UUID) -> bool:
        row = self.get_contact(contact_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ----- Technicians ----------------------------------------------------

    def create_technician(self, payload: TechnicianCreate) -> Technician:
        org = self.get_organization(payload.organization_id)
        if not org:
            raise ValueError("Organization not found")
        assigned = (
            [str(x) for x in payload.assigned_tenant_ids]
            if payload.assigned_tenant_ids
            else None
        )
        row = Technician(
            tenant_id=org.tenant_id,
            organization_id=org.id,
            user_id=payload.user_id,
            display_name=payload.display_name,
            email=payload.email,
            phone=payload.phone,
            title=payload.title,
            status=payload.status,
            skills=payload.skills,
            role_name=payload.role_name,
            is_msp_admin=payload.is_msp_admin,
            assigned_tenant_ids=assigned,
            notes=payload.notes,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_technicians(
        self,
        *,
        organization_id: UUID | None = None,
        tenant_id: UUID | None = None,
        status: str | None = None,
    ) -> list[Technician]:
        q = self.db.query(Technician)
        if organization_id:
            q = q.filter(Technician.organization_id == organization_id)
        if tenant_id:
            q = q.filter(Technician.tenant_id == tenant_id)
        if status:
            q = q.filter(Technician.status == status)
        return q.order_by(Technician.display_name).all()

    def get_technician(self, tech_id: UUID) -> Technician | None:
        return self.db.query(Technician).filter(Technician.id == tech_id).first()

    def update_technician(
        self, tech_id: UUID, payload: TechnicianUpdate
    ) -> Technician | None:
        row = self.get_technician(tech_id)
        if not row:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "assigned_tenant_ids" in data and data["assigned_tenant_ids"] is not None:
            data["assigned_tenant_ids"] = [
                str(x) for x in data["assigned_tenant_ids"]
            ]
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_technician(self, tech_id: UUID) -> bool:
        row = self.get_technician(tech_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ----- Branding -------------------------------------------------------

    def get_branding(self, tenant_id: UUID) -> TenantBranding | None:
        return (
            self.db.query(TenantBranding)
            .filter(TenantBranding.tenant_id == tenant_id)
            .first()
        )

    def upsert_branding(
        self, tenant_id: UUID, payload: BrandingUpdate
    ) -> TenantBranding:
        org = self.get_organization_by_tenant(tenant_id)
        if not org:
            raise ValueError("Organization not found for tenant")
        row = self.get_branding(tenant_id)
        data = payload.model_dump(exclude_unset=True)
        if row is None:
            row = TenantBranding(
                tenant_id=tenant_id,
                organization_id=org.id,
                **data,
            )
            self.db.add(row)
        else:
            for k, v in data.items():
                setattr(row, k, v)
            row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    # ----- Billing plans --------------------------------------------------

    def create_plan(self, payload: BillingPlanCreate) -> BillingPlan:
        existing = (
            self.db.query(BillingPlan)
            .filter(BillingPlan.code == payload.code)
            .first()
        )
        if existing:
            raise ValueError("Plan code already exists")
        row = BillingPlan(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            interval=payload.interval,
            price=payload.price,
            currency=payload.currency,
            included_devices=payload.included_devices,
            included_users=payload.included_users,
            features=payload.features,
            active=payload.active,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_plans(self, *, active_only: bool = False) -> list[BillingPlan]:
        q = self.db.query(BillingPlan)
        if active_only:
            q = q.filter(BillingPlan.active.is_(True))
        return q.order_by(BillingPlan.name).all()

    def get_plan(self, plan_id: UUID) -> BillingPlan | None:
        return self.db.query(BillingPlan).filter(BillingPlan.id == plan_id).first()

    def update_plan(
        self, plan_id: UUID, payload: BillingPlanUpdate
    ) -> BillingPlan | None:
        row = self.get_plan(plan_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_plan(self, plan_id: UUID) -> bool:
        row = self.get_plan(plan_id)
        if not row:
            return False
        row.active = False
        self.db.commit()
        return True

    # ----- Subscriptions --------------------------------------------------

    def create_subscription(
        self, payload: SubscriptionCreate
    ) -> TenantSubscription:
        org = self.get_organization(payload.organization_id)
        if not org:
            raise ValueError("Organization not found")
        existing = (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.tenant_id == org.tenant_id)
            .first()
        )
        if existing:
            raise ValueError("Subscription already exists for this tenant")
        row = TenantSubscription(
            tenant_id=org.tenant_id,
            organization_id=org.id,
            plan_id=payload.plan_id,
            status=payload.status,
            seats=payload.seats,
            device_limit=payload.device_limit,
            trial_ends_at=payload.trial_ends_at,
            external_customer_id=payload.external_customer_id,
            external_subscription_id=payload.external_subscription_id,
            meta=payload.meta,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_subscription(self, tenant_id: UUID) -> TenantSubscription | None:
        return (
            self.db.query(TenantSubscription)
            .filter(TenantSubscription.tenant_id == tenant_id)
            .first()
        )

    def update_subscription(
        self, tenant_id: UUID, payload: SubscriptionUpdate
    ) -> TenantSubscription | None:
        row = self.get_subscription(tenant_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def seed_default_plans(self) -> list[BillingPlan]:
        defaults = [
            {
                "code": "starter",
                "name": "Starter",
                "description": "Up to 25 devices",
                "price": 99.0,
                "included_devices": 25,
                "included_users": 3,
                "features": {"reporting": True, "remote_access": True},
            },
            {
                "code": "professional",
                "name": "Professional",
                "description": "Up to 100 devices",
                "price": 299.0,
                "included_devices": 100,
                "included_users": 10,
                "features": {
                    "reporting": True,
                    "remote_access": True,
                    "compliance": True,
                },
            },
            {
                "code": "enterprise",
                "name": "Enterprise",
                "description": "Unlimited devices",
                "price": 799.0,
                "included_devices": None,
                "included_users": None,
                "features": {
                    "reporting": True,
                    "remote_access": True,
                    "compliance": True,
                    "white_label": True,
                },
            },
        ]
        created: list[BillingPlan] = []
        for item in defaults:
            existing = (
                self.db.query(BillingPlan)
                .filter(BillingPlan.code == item["code"])
                .first()
            )
            if existing:
                created.append(existing)
                continue
            row = BillingPlan(**item, interval="monthly", currency="USD", active=True)
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for r in created:
            self.db.refresh(r)
        return created
