from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.permission import Permission
from app.db.seeds.role_permission_seed import seed_role_permissions

# Canonical permission catalogue
PERMISSIONS = [
    "device.read",
    "device.create",
    "device.update",
    "device.delete",
    "user.read",
    "user.create",
    "user.update",
    "user.delete",
    "role.manage",
    "permission.manage",
    "audit.read",
    "tenant.read",
    "tenant.manage",
    "agent.command",
    "agent.manage",
    "billing.manage",
    "platform.heal",
]

# ============================================================
# Active roles only — diminishing hierarchy (highest → lowest)
# ============================================================
#   1. enterprise_admin  rank 100  full platform owner
#   2. system_admin      rank  80  operator (no role/billing ownership)
#
# Legacy names (admin, super_admin, technician, viewer, agent) are
# not seeded. Existing DB rows are left alone.
ROLES = [
    "enterprise_admin",
    "system_admin",
]

ROLE_RANK = {
    "enterprise_admin": 100,
    "system_admin": 80,
}

ROLE_DESCRIPTIONS = {
    "enterprise_admin": (
        "Rank 100 — highest. Full control of Bhudi Online: users, roles, "
        "billing, tenants, agents, and platform heal."
    ),
    "system_admin": (
        "Rank 80 — operator. Day-to-day admin of devices, agents, users, "
        "and tenants. Cannot manage roles, permissions, or billing."
    ),
}


def seed_permissions(db: Session) -> dict[str, Permission]:
    permission_map: dict[str, Permission] = {}
    for permission_name in PERMISSIONS:
        permission = db.query(Permission).filter(Permission.name == permission_name).first()
        if not permission:
            resource, action = (
                permission_name.split(".", 1) if "." in permission_name else (permission_name, "read")
            )
            permission = Permission(
                name=permission_name,
                resource=resource,
                action=action,
                description=f"Allows {permission_name}",
            )
            db.add(permission)
            db.flush()
        permission_map[permission_name] = permission
    return permission_map


def seed_roles(db: Session) -> dict[str, Role]:
    role_map: dict[str, Role] = {}
    for role_name in ROLES:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(
                name=role_name,
                description=ROLE_DESCRIPTIONS.get(role_name, f"{role_name} role"),
                system=True,
            )
            db.add(role)
            db.flush()
        else:
            role.description = ROLE_DESCRIPTIONS.get(role_name, role.description)
            role.system = True
        role_map[role_name] = role
    return role_map


def seed_rbac(db: Session) -> None:
    permissions = seed_permissions(db)
    roles = seed_roles(db)
    seed_role_permissions(db, roles, permissions)
    db.commit()
