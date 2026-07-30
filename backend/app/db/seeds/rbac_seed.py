from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.permission import Permission
from app.db.seeds.role_permission_seed import (
    seed_role_permissions,
)

# ==========================================================
# Default Permissions
# ==========================================================

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
]


# ==========================================================
# Default Roles
# ==========================================================

ROLES = [
    "super_admin",
    "admin",
    "technician",
    "viewer",
    "agent",
]


def seed_permissions(
    db: Session,
) -> dict[str, Permission]:
    """
    Create missing permissions.

    Returns:
        {
            "device.read": Permission(...)
        }
    """

    permission_map = {}

    for permission_name in PERMISSIONS:

        permission = (
            db.query(Permission)
            .filter(
                Permission.name == permission_name
            )
            .first()
        )

        if not permission:
            permission = Permission(
                name=permission_name,
                description=(
                    f"Allows {permission_name}"
                ),
            )

            db.add(permission)
            db.flush()

        permission_map[permission_name] = permission

    return permission_map



def seed_roles(
    db: Session,
) -> dict[str, Role]:
    """
    Create missing roles.
    """

    role_map = {}

    for role_name in ROLES:

        role = (
            db.query(Role)
            .filter(
                Role.name == role_name
            )
            .first()
        )

        if not role:
            role = Role(
                name=role_name,
                description=(
                    f"{role_name} role"
                ),
            )

            db.add(role)
            db.flush()

        role_map[role_name] = role

    return role_map



def seed_rbac(
    db: Session,
):
    """
    Main RBAC seed entry point.
    """
    permissions = seed_permissions(db)

    roles = seed_roles(db)

    seed_role_permissions(
        db,
        roles,
        permissions,
    )

    db.commit()