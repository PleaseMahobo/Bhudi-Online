from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.alert_engine import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    EscalationPolicyCreate,
    EscalationPolicyUpdate,
    EscalationPolicyResponse,
)
from app.services.alert_rule_service import AlertRuleService

router = APIRouter(prefix="/alert-engine", tags=["Alert Engine"])


# =========================================================
# Escalation Policies
# =========================================================

@router.post(
    "/escalation-policies",
    response_model=EscalationPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_escalation_policy(
    payload: EscalationPolicyCreate,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    return service.create_escalation_policy(payload)


@router.get(
    "/escalation-policies",
    response_model=list[EscalationPolicyResponse],
)
def list_escalation_policies(
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    return service.list_escalation_policies(enabled_only=enabled_only)


@router.get(
    "/escalation-policies/{policy_id}",
    response_model=EscalationPolicyResponse,
)
def get_escalation_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    policy = service.get_escalation_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Escalation policy not found")
    return policy


@router.patch(
    "/escalation-policies/{policy_id}",
    response_model=EscalationPolicyResponse,
)
def update_escalation_policy(
    policy_id: UUID,
    payload: EscalationPolicyUpdate,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    policy = service.update_escalation_policy(policy_id, payload)
    if not policy:
        raise HTTPException(status_code=404, detail="Escalation policy not found")
    return policy


@router.delete(
    "/escalation-policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_escalation_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    success = service.delete_escalation_policy(policy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Escalation policy not found")


# =========================================================
# Alert Rules
# =========================================================

@router.post(
    "/rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert_rule(
    payload: AlertRuleCreate,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    return service.create_alert_rule(payload)


@router.get(
    "/rules",
    response_model=list[AlertRuleResponse],
)
def list_alert_rules(
    enabled_only: bool = False,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    return service.list_alert_rules(enabled_only=enabled_only)


@router.get(
    "/rules/{rule_id}",
    response_model=AlertRuleResponse,
)
def get_alert_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    rule = service.get_alert_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.patch(
    "/rules/{rule_id}",
    response_model=AlertRuleResponse,
)
def update_alert_rule(
    rule_id: UUID,
    payload: AlertRuleUpdate,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    rule = service.update_alert_rule(rule_id, payload)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_alert_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
):
    service = AlertRuleService(db)
    success = service.delete_alert_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert rule not found")
