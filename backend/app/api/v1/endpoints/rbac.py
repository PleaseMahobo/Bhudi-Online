from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permission
from app.database.session import get_db
from app.models.user import User
from app.services.authorization_service import AuthorizationService

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get("/permissions")
def list_permissions(
    current_user: User = Depends(require_permission("permission.manage")),
    db: Session = Depends(get_db),
):
    try:
        service = AuthorizationService(db)
        return {
            "permissions": [
                {
                    "name": permission.name,
                    "resource": permission.resource,
                    "action": permission.action,
                    "description": permission.description,
                }
                for permission in service.permission_repository.list()
            ]
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RBAC data unavailable: database connection failed",
        ) from exc


@router.get("/me")
def my_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = AuthorizationService(db)
        return {
            "user_id": str(current_user.id),
            "roles": [role.name for role in service.get_user_roles(current_user.id)],
            "permissions": sorted(service.get_user_permissions(current_user.id)),
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RBAC data unavailable: database connection failed",
        ) from exc
