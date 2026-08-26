from __future__ import annotations

import os
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, engine
from app.models.audit_trail import AuditTrail
from app.models.base import Base
from app.models.alert_rule import AlertRule
from app.models.asset_management import Asset, Contract, Vendor
from app.models.device_management import (
    ConfigurationProfile,
    DeviceGroup,
    DevicePolicy,
    DeviceTag,
    DynamicDeviceGroup,
    ManagedDevice,
    MaintenanceWindow,
    PatchRing,
    PatchRollout,
)
from app.models.monitoring import MonitoringAlert, MonitoringCheck
from app.models.action import Action
from app.models.agent import Agent
from app.models.agent_command import AgentCommand
from app.models.automation_log import AutomationLog
from app.models.device import Device
from app.models.escalation_policy import EscalationPolicy
from app.models.incident import Incident
from app.models.response_action import ResponseAction
from app.models.script import Script
from app.models.script_task import ScriptTask
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.secret_entry import SecretEntry
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.models.msp import Organization, Technician
from app.models.itsm import ServiceTicket, TicketAssetLink, TicketWorkNote
from app.models.itsm_extended import (
    ITSMSLAPolicy,
    ITSMAssignmentGroup,
    ITSMTicketHistory,
    ITSMTicketAttachment,
)
from app.models.itsm_operational import ITSMTicketAssignment, ITSMSLAEscalation
from app.db.seeds.rbac_seed import seed_rbac
from app.core.security import hash_password


def _bootstrap_metadata_for_engine() -> MetaData:
    if engine.dialect.name == "sqlite":
        metadata = MetaData()
        for model in [
            Tenant,
            User,
            Role,
            Permission,
            RolePermission,
            UserRole,
            RefreshToken,
            AuditTrail,
            SecretEntry,
            ManagedDevice,
            DeviceGroup,
            DynamicDeviceGroup,
            DeviceTag,
            DevicePolicy,
            ConfigurationProfile,
            MaintenanceWindow,
            PatchRing,
            PatchRollout,
            EscalationPolicy,
            AlertRule,
            MonitoringCheck,
            MonitoringAlert,
            Device,
            Agent,
            AgentCommand,
            Incident,
            Action,
            AutomationLog,
            ResponseAction,
            Script,
            ScriptTask,
            ServiceTicket,
            TicketAssetLink,
            TicketWorkNote,
            ITSMSLAPolicy,
            ITSMAssignmentGroup,
            ITSMTicketHistory,
            ITSMTicketAttachment,
            ITSMTicketAssignment,
            ITSMSLAEscalation,
            Asset,
            Contract,
            Vendor,
            Organization,
            Technician,
        ]:
            model.__table__.to_metadata(metadata)
        return metadata
    return Base.metadata


def ensure_alert_engine_schema() -> list[str]:
    """Add columns introduced after the original alert_rules migration.

    create_all() does not ALTER existing tables; production DBs created from the
    first migration lack remediation_actions, which makes GET /rules return 500.
    """
    applied: list[str] = []
    if engine is None:
        return applied
    statements = [
        (
            "alert_rules.remediation_actions",
            "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS remediation_actions JSON",
        ),
    ]
    try:
        from sqlalchemy import text as sql_text

        with engine.begin() as conn:
            for label, stmt in statements:
                try:
                    conn.execute(sql_text(stmt))
                    applied.append(label)
                except Exception as col_exc:
                    print(f"[bootstrap] skip {label}: {col_exc}")
    except Exception as exc:
        print(f"[bootstrap] ensure_alert_engine_schema failed: {exc}")
    return applied


def initialize_database() -> dict[str, Any]:
    """Create tables and seed RBAC/auth data when the database is reachable."""
    try:
        _bootstrap_metadata_for_engine().create_all(bind=engine)
        ensure_alert_engine_schema()
    except SQLAlchemyError as exc:
        return {"status": "skipped", "reason": f"database unavailable: {exc}"}

    db: Session = SessionLocal()
    try:
        seed_rbac(db)
        admin_email = os.getenv("BHUDI_ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("BHUDI_ADMIN_PASSWORD", "StrongPassword123!")
        existing = db.query(User).filter(User.email == admin_email).first()
        force_reset = os.getenv("BHUDI_ADMIN_FORCE_RESET", "").strip().lower() in ("1", "true", "yes")
        if existing is None:
            admin_user = User(email=admin_email, password_hash=hash_password(admin_password), first_name="System", last_name="Admin", role="admin", active=True)
            db.add(admin_user)
            db.flush()
            db.refresh(admin_user)
        else:
            admin_user = existing
            if force_reset and admin_password:
                admin_user.password_hash = hash_password(admin_password)
                admin_user.active = True
                admin_user.role = getattr(admin_user, "role", None) or "admin"
                if hasattr(admin_user, "failed_login_attempts"):
                    admin_user.failed_login_attempts = 0
                if hasattr(admin_user, "locked_until"):
                    admin_user.locked_until = None
                print(f"[bootstrap] forced password reset for {admin_email}")
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is not None:
            existing_assignment = db.query(UserRole).filter(UserRole.user_id == admin_user.id, UserRole.role_id == admin_role.id).first()
            if existing_assignment is None:
                db.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
        db.commit()
        return {"status": "initialized", "admin_email": admin_email}
    except SQLAlchemyError as exc:
        return {"status": "skipped", "reason": f"seed failed: {exc}"}
    finally:
        db.close()
