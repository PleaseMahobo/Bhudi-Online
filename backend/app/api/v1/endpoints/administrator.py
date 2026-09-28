from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.services.authorization_service import AuthorizationService

router = APIRouter(prefix="/admin", tags=["Administrator Portal"])


class UserAdminUpdate(BaseModel):
    role: str | None = Field(default=None, min_length=1, max_length=100)
    tenant_id: UUID | None = None
    active: bool | None = None


def _require_platform_admin(current_user: User, db: Session) -> User:
    # The administrator portal is platform-wide. Only the highest seeded role
    # may enumerate or mutate users, tenants, roles and permissions.
    AuthorizationService(db).require_min_rank(current_user.id, 100)
    return current_user


@router.get("/overview")
def overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_platform_admin(current_user, db)
    users = db.query(User).count()
    active_users = db.query(User).filter(User.active.is_(True)).count()
    tenants = db.query(Tenant).count()
    roles = db.query(Role).count()
    permissions = db.query(Permission).count()
    return {
        "users": users,
        "active_users": active_users,
        "inactive_users": users - active_users,
        "tenants": tenants,
        "roles": roles,
        "permissions": permissions,
    }


@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_platform_admin(current_user, db)
    rows = (
        db.query(User, Tenant.name.label("tenant_name"))
        .outerjoin(Tenant, Tenant.id == User.tenant_id)
        .order_by(User.email.asc())
        .all()
    )
    authz = AuthorizationService(db)
    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "roles": [role.name for role in authz.get_user_roles(user.id)],
                "active": bool(user.active),
                "mfa_enabled": bool(user.mfa_enabled),
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "tenant_name": tenant_name,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            for user, tenant_name in rows
        ]
    }


@router.get("/tenants")
def list_tenants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_platform_admin(current_user, db)
    user_counts = dict(
        db.query(User.tenant_id, func.count(User.id))
        .filter(User.tenant_id.isnot(None))
        .group_by(User.tenant_id)
        .all()
    )
    return {
        "tenants": [
            {
                "id": str(tenant.id),
                "name": tenant.name,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
                "user_count": int(user_counts.get(tenant.id, 0)),
                "agent_count": len(tenant.agents),
                "device_count": len(tenant.devices),
            }
            for tenant in db.query(Tenant).order_by(Tenant.name.asc()).all()
        ]
    }


@router.get("/roles")
def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_platform_admin(current_user, db)
    roles = db.query(Role).order_by(Role.name.asc()).all()
    return {
        "roles": [
            {
                "id": str(role.id),
                "name": role.name,
                "description": role.description,
                "system": bool(role.system),
                "permissions": [
                    permission.name
                    for permission in db.query(Permission)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .filter(RolePermission.role_id == role.id)
                    .order_by(Permission.name.asc())
                    .all()
                ],
            }
            for role in roles
        ]
    }


@router.get("/permissions")
def list_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_platform_admin(current_user, db)
    return {
        "permissions": [
            {
                "id": str(permission.id),
                "name": permission.name,
                "resource": permission.resource,
                "action": permission.action,
                "description": permission.description,
            }
            for permission in db.query(Permission).order_by(Permission.name.asc()).all()
        ]
    }


@router.patch("/users/{user_id}")
def update_user(
    user_id: UUID,
    payload: UserAdminUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_platform_admin(current_user, db)
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")

    if payload.tenant_id is not None and db.get(Tenant, payload.tenant_id) is None:
        raise HTTPException(404, "Tenant not found")

    if payload.role is not None:
        role = db.query(Role).filter(func.lower(Role.name) == payload.role.strip().lower()).first()
        if role is None:
            raise HTTPException(400, "Unknown RBAC role")

        # Do not allow this endpoint to create a second top-level platform
        # administrator accidentally; enterprise_admin remains explicitly
        # controlled by the platform administrator.
        existing = (
            db.query(UserRole)
            .filter(UserRole.user_id == target.id)
            .all()
        )
        for assignment in existing:
            db.delete(assignment)
        db.flush()
        target.role = role.name
        db.add(UserRole(user_id=target.id, role_id=role.id))

    if payload.tenant_id is not None:
        target.tenant_id = payload.tenant_id

    if payload.active is not None:
        if target.id == current_user.id and payload.active is False:
            raise HTTPException(400, "You cannot deactivate your own administrator account")
        target.active = payload.active

    db.add(target)
    db.commit()
    db.refresh(target)

    authz = AuthorizationService(db)
    return {
        "id": str(target.id),
        "email": target.email,
        "role": target.role,
        "roles": [role.name for role in authz.get_user_roles(target.id)],
        "active": bool(target.active),
        "tenant_id": str(target.tenant_id) if target.tenant_id else None,
    }
