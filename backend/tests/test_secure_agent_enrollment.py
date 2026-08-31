from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock, call, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.agent import Agent
from app.models.agent_enrollment import AgentEnrollment
from app.models.tenant import Tenant
from app.services.entitlement_service import Entitlement
from app.services.agent_enrollment_service import AgentEnrollmentService


def _enrollment(tenant_id):
    return AgentEnrollment(
        id=uuid4(),
        tenant_id=tenant_id,
        token_hash="hash",
        revoked=False,
    )


def test_secure_enrollment_runs_credential_tenant_machine_agent_commit():
    tenant_id = uuid4()
    enrollment = _enrollment(tenant_id)
    tenant = Tenant(id=tenant_id, name="Customer A")
    db = MagicMock()
    db.scalar.side_effect = [enrollment, None, 0]
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.get.return_value = tenant
    db.scalar.side_effect = [enrollment, None, 0]
    # Paid seat available: enrollment should remain approved/trusted.
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(status="active", device_limit=1, meta={"plan_code": "starter"})

    service = AgentEnrollmentService(db)
    row, agent_token, returned_tenant = service.enroll_agent(
        enrollment_secret="customer-token",
        hostname="CUSTOMER-PC",
        agent_version="1.0.0",
        platform="windows",
        machine_guid="  MACHINE-GUID-01  ",
    )

    assert isinstance(row, Agent)
    assert row.tenant_id == tenant_id
    assert row.machine_guid == "machine-guid-01"
    assert row.hostname == "CUSTOMER-PC"
    assert row.registration_state == "approved"
    assert returned_tenant == tenant_id
    assert agent_token == row.enrollment_token
    assert enrollment.agent_id == row.id

    db.get.assert_called_once_with(Tenant, tenant_id)
    assert db.scalar.call_count == 3
    db.flush.assert_called_once_with()
    db.commit.assert_called_once_with()
    assert db.method_calls.index(call.flush()) < db.method_calls.index(call.commit())


def test_secure_enrollment_rejects_machine_owned_by_another_tenant():
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    enrollment = _enrollment(tenant_id)
    tenant = Tenant(id=tenant_id, name="Customer A")
    existing = SimpleNamespace(tenant_id=other_tenant_id, machine_guid="machine-guid-01")
    db = Mock()
    db.scalar.side_effect = [enrollment, existing]
    db.get.return_value = tenant

    with pytest.raises(HTTPException) as exc:
        AgentEnrollmentService(db).enroll_agent(
            enrollment_secret="customer-token",
            hostname="CUSTOMER-PC",
            agent_version="1.0.0",
            platform="windows",
            machine_guid="machine-guid-01",
        )

    assert exc.value.status_code == 409
    db.flush.assert_not_called()
    db.commit.assert_not_called()


def test_mark_used_does_not_break_atomic_transaction():
    db = Mock()
    service = AgentEnrollmentService(db)
    record = _enrollment(uuid4())
    agent_id = uuid4()

    service.mark_used(record, agent_id)

    assert record.agent_id == agent_id
    db.add.assert_called_once_with(record)
    db.commit.assert_not_called()


def test_integrity_failure_is_available_for_endpoint_translation():
    db = MagicMock()
    db.flush.side_effect = IntegrityError("statement", {}, Exception("duplicate machine"))
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(status="active", device_limit=1, meta={"plan_code": "starter"})
    service = AgentEnrollmentService(db)
    tenant_id = uuid4()
    enrollment = _enrollment(tenant_id)
    db.scalar.side_effect = [enrollment, None, 0]
    db.get.return_value = Tenant(id=tenant_id, name="Customer A")

    with pytest.raises(IntegrityError):
        service.enroll_agent(
            enrollment_secret="customer-token",
            hostname="CUSTOMER-PC",
            agent_version="1.0.0",
            platform="windows",
            machine_guid="machine-guid-01",
        )

    db.commit.assert_not_called()
