"""Customer wizard and user invite helpers for MSP multi-tenant."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import generate_password, hash_password
from app.models.msp import Contact, Organization, Site
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.msp import (
    ContactCreate,
    CustomerWizardCreate,
    InviteUserRequest,
    InviteUserResponse,
    OrganizationCreate,
    SiteCreate,
)
from app.services.msp_service import MspService


class MspCustomerOps:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.msp = MspService(db)

    def create_customer_wizard(self, payload: CustomerWizardCreate) -> dict:
        """Atomic org + site + primary contact."""
        org = self.msp.create_organization(
            OrganizationCreate(
                name=payload.name,
                org_type=payload.org_type,
                status=payload.status,
                email=payload.email,
                phone=payload.phone,
                website=payload.website,
                notes=payload.notes,
            )
        )
        site = self.msp.create_site(
            SiteCreate(
                organization_id=org.id,
                name=payload.site.name,
                code=payload.site.code,
                address_line1=payload.site.address_line1,
                city=payload.site.city,
                state=payload.site.state,
                postal_code=payload.site.postal_code,
                country=payload.site.country,
                phone=payload.site.phone,
                enabled=True,
            )
        )
        contact = self.msp.create_contact(
            ContactCreate(
                organization_id=org.id,
                site_id=site.id,
                first_name=payload.contact.first_name,
                last_name=payload.contact.last_name,
                email=payload.contact.email,
                phone=payload.contact.phone,
                title=payload.contact.title,
                contact_type="primary",
                is_primary=True,
                enabled=True,
            )
        )
        return {"organization": org, "site": site, "contact": contact}

    def invite_user(self, payload: InviteUserRequest) -> InviteUserResponse:
        """Create (or update) a Bhudi user bound to a tenant and RBAC role.

        Login path: user signs in with Supabase using the same email; Bhudi
        maps via email and applies tenant_id + role already set here.
        Temporary password is returned once for admin hand-off / recovery.
        """
        tenant = self.db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
        if not tenant:
            raise ValueError("Tenant not found")

        email = str(payload.email).strip().lower()
        users = UserRepository(self.db)
        existing = users.get_by_email(email)

        temp_password = payload.temporary_password or generate_password()
        try:
            password_hash = hash_password(temp_password)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        role_name = payload.role.strip().lower()
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if role is None:
            role = Role(name=role_name, description=f"Auto-created role: {role_name}", system=False)
            self.db.add(role)
            self.db.flush()

        if existing:
            existing.tenant_id = payload.tenant_id
            existing.role = role_name
            existing.active = True
            if payload.first_name:
                existing.first_name = payload.first_name
            if payload.last_name:
                existing.last_name = payload.last_name
            existing.password_hash = password_hash
            user = existing
        else:
            user = User(
                email=email,
                password_hash=password_hash,
                first_name=payload.first_name,
                last_name=payload.last_name,
                role=role_name,
                active=True,
                tenant_id=payload.tenant_id,
            )
            self.db.add(user)
            self.db.flush()

        already = (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user.id, UserRole.role_id == role.id)
            .first()
        )
        if not already:
            self.db.add(UserRole(user_id=user.id, role_id=role.id))

        self.db.commit()
        self.db.refresh(user)

        return InviteUserResponse(
            user_id=user.id,
            email=user.email,
            role=role_name,
            tenant_id=payload.tenant_id,
            temporary_password=temp_password,
            message=(
                "User bound to tenant and role. Share the temporary password securely. "
                "User must sign in with Supabase using this email; Bhudi maps the identity on first login."
            ),
        )
