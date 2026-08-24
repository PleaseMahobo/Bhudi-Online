"""Customer wizard and user invite endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database.session import get_db
from app.schemas.msp import (
    ContactResponse,
    CustomerWizardCreate,
    CustomerWizardResponse,
    InviteUserRequest,
    InviteUserResponse,
    OrganizationResponse,
    SiteResponse,
)
from app.services.msp_customer_ops import MspCustomerOps

router = APIRouter(prefix="/msp", tags=["MSP Multi-Tenant"])


@router.post(
    "/customers/wizard",
    response_model=CustomerWizardResponse,
    status_code=201,
)
def create_customer_wizard(
    payload: CustomerWizardCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin()),
):
    try:
        result = MspCustomerOps(db).create_customer_wizard(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return CustomerWizardResponse(
        organization=OrganizationResponse.model_validate(result["organization"]),
        site=SiteResponse.model_validate(result["site"]),
        contact=ContactResponse.model_validate(result["contact"]),
    )


@router.post(
    "/users/invite",
    response_model=InviteUserResponse,
    status_code=201,
)
def invite_user(
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin()),
):
    try:
        return MspCustomerOps(db).invite_user(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
