from __future__ import annotations

import os
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, engine
from app.models.base import Base
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.db.seeds.rbac_seed import seed_rbac
from app.core.security import hash_password


def initialize_database() -> dict[str, Any]:
    """Create tables and seed RBAC/auth data when the database is reachable."""
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as exc:
        return {"status": "skipped", "reason": f"database unavailable: {exc}"}

    db: Session = SessionLocal()
    try:
        seed_rbac(db)
        admin_email = os.getenv("BHUDI_ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("BHUDI_ADMIN_PASSWORD", "StrongPassword123!")

        existing = db.query(User).filter(User.email == admin_email).first()
        if existing is None:
            admin_user = User(
                email=admin_email,
                password_hash=hash_password(admin_password),
                first_name="System",
                last_name="Admin",
                role="admin",
                active=True,
            )
            db.add(admin_user)
            db.flush()
            db.refresh(admin_user)
        else:
            admin_user = existing

        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is not None:
            existing_assignment = (
                db.query(UserRole)
                .filter(
                    UserRole.user_id == admin_user.id,
                    UserRole.role_id == admin_role.id,
                )
                .first()
            )
            if existing_assignment is None:
                db.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))

        db.commit()
        return {"status": "initialized", "admin_email": admin_email}
    except SQLAlchemyError as exc:
        return {"status": "skipped", "reason": f"seed failed: {exc}"}
    finally:
        db.close()
