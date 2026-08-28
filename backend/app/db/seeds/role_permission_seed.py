from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.role_permission import RolePermission

# Diminishing matrix (highest → lowest).
# enterprise_admin inherits everything; system_admin is a strict subset.
ROLE_PERMISSIONS: dict[str, list[str]] = {
    # Rank 100 — platform owner
    "enterprise_admin": ["*"],
    # Rank 80 — operator (no role / permission / billing ownership)
    "system_admin": [
        "device.read",
        "device.create",
        "device.update",
        "device.delete",
        "user.read",
        "user.create",
        "user.update",
        # no user.delete
        "audit.read",
        "tenant.read",
        # no tenant.manage
        "agent.command",
        "agent.manage",
        # no role.manage, permission.manage, billing.manage, platform.heal
    ],
}


def seed_role_permissions(db: Session, roles: dict, permissions: dict) -> None:
    for role_name, permission_names in ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if not role:
            continue

        names = list(permissions.keys()) if "*" in permission_names else list(permission_names)

        for permission_name in names:
            permission = permissions.get(permission_name)
            if not permission:
                continue

            exists = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
                .first()
            )
            if exists:
                continue

            db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()
