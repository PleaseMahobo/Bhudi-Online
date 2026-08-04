from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.role_permission import RolePermission


# ==========================================================
# Role Permission Matrix
# ==========================================================

ROLE_PERMISSIONS = {
    "super_admin": [
        "*",
    ],

    "admin": [
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
    ],

    "technician": [
        "device.read",
        "device.update",

        "agent.command",
        "audit.read",
    ],

    "viewer": [
        "device.read",
        "audit.read",
    ],

    "agent": [
        "device.read",
        "agent.manage",
    ],
}


def seed_role_permissions(
    db: Session,
    roles: dict,
    permissions: dict,
):
    """
    Create RolePermission mappings.

    roles:
        {
            "admin": Role(...)
        }

    permissions:
        {
            "device.read": Permission(...)
        }
    """

    for role_name, permission_names in ROLE_PERMISSIONS.items():

        role = roles.get(role_name)

        if not role:
            continue


        # Super admin wildcard
        if "*" in permission_names:
            permission_names = permissions.keys()


        for permission_name in permission_names:

            permission = permissions.get(
                permission_name
            )

            if not permission:
                continue


            exists = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role_id
                    == role.id,
                    RolePermission.permission_id
                    == permission.id,
                )
                .first()
            )


            if exists:
                continue


            mapping = RolePermission(
                role_id=role.id,
                permission_id=permission.id,
            )

            db.add(mapping)


    db.commit()