from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alert_rule import AlertRule
from app.models.escalation_policy import EscalationPolicy
from app.schemas.alert_engine import (
    AlertRuleCreate,
    AlertRuleUpdate,
    EscalationPolicyCreate,
    EscalationPolicyUpdate,
)


def _actions_to_json(actions: list[Any] | None) -> list[dict[str, Any]]:
    if not actions:
        return []
    out: list[dict[str, Any]] = []
    for a in actions:
        if hasattr(a, "model_dump"):
            out.append(a.model_dump())
        elif isinstance(a, dict):
            out.append(a)
    return out


class AlertRuleService:
    def __init__(self, db: Session):
        self.db = db

    # =========================================================
    # Escalation Policies
    # =========================================================

    def create_escalation_policy(self, data: EscalationPolicyCreate) -> EscalationPolicy:
        policy = EscalationPolicy(
            name=data.name,
            description=data.description,
            levels=[level.model_dump() for level in data.levels],
            enabled=data.enabled,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def get_escalation_policy(self, policy_id: UUID) -> EscalationPolicy | None:
        return self.db.get(EscalationPolicy, policy_id)

    def list_escalation_policies(self, enabled_only: bool = False) -> Sequence[EscalationPolicy]:
        query = self.db.query(EscalationPolicy)
        if enabled_only:
            query = query.filter(EscalationPolicy.enabled.is_(True))
        return query.order_by(EscalationPolicy.name).all()

    def update_escalation_policy(
        self, policy_id: UUID, data: EscalationPolicyUpdate
    ) -> EscalationPolicy | None:
        policy = self.get_escalation_policy(policy_id)
        if not policy:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "levels" in update_data and update_data["levels"] is not None:
            update_data["levels"] = [
                level.model_dump() if hasattr(level, "model_dump") else level
                for level in update_data["levels"]
            ]

        for key, value in update_data.items():
            setattr(policy, key, value)

        self.db.commit()
        self.db.refresh(policy)
        return policy

    def delete_escalation_policy(self, policy_id: UUID) -> bool:
        policy = self.get_escalation_policy(policy_id)
        if not policy:
            return False
        self.db.delete(policy)
        self.db.commit()
        return True

    # =========================================================
    # Alert Rules
    # =========================================================

    def create_alert_rule(self, data: AlertRuleCreate) -> AlertRule:
        payload = data.model_dump()
        payload["remediation_actions"] = _actions_to_json(payload.get("remediation_actions"))
        rule = AlertRule(**payload)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_alert_rule(self, rule_id: UUID) -> AlertRule | None:
        return self.db.get(AlertRule, rule_id)

    def list_alert_rules(self, enabled_only: bool = False) -> Sequence[AlertRule]:
        query = self.db.query(AlertRule)
        if enabled_only:
            query = query.filter(AlertRule.enabled.is_(True))
        return query.order_by(AlertRule.priority.asc(), AlertRule.name).all()

    def update_alert_rule(self, rule_id: UUID, data: AlertRuleUpdate) -> AlertRule | None:
        rule = self.get_alert_rule(rule_id)
        if not rule:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "remediation_actions" in update_data:
            update_data["remediation_actions"] = _actions_to_json(
                update_data.get("remediation_actions")
            )

        for key, value in update_data.items():
            setattr(rule, key, value)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_alert_rule(self, rule_id: UUID) -> bool:
        rule = self.get_alert_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True

    def find_matching_rules(
        self,
        *,
        provider: str | None = None,
        check_type: str | None = None,
        target: str | None = None,
        metric_name: str | None = None,
    ) -> list[AlertRule]:
        """Return all enabled rules that match the given criteria."""
        rules = self.list_alert_rules(enabled_only=True)
        matched: list[AlertRule] = []

        for rule in rules:
            if rule.provider and provider and rule.provider != provider:
                continue
            if rule.check_type and check_type and rule.check_type != check_type:
                continue
            if rule.target and target and rule.target != target:
                continue
            if rule.metric_name and metric_name and rule.metric_name != metric_name:
                continue
            matched.append(rule)

        return matched
