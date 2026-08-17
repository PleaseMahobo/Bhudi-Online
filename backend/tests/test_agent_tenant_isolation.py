from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository
from app.services import agent_service
from app.services.agent_enrollment_service import AgentEnrollmentService


class CaptureSession:
    def __init__(self):
        self.statement = None

    def scalar(self, statement):
        self.statement = statement
        return None


class FakeDB:
    def add(self, _obj):
        pass

    def commit(self):
        pass

    def refresh(self, _obj):
        pass

    def flush(self):
        pass


class FakeAgents:
    def __init__(self, existing=None):
        self.existing = existing

    def get_by_device(self, _device_id, **_kwargs):
        return self.existing


class FakeDevices:
    def __init__(self, device):
        self.device = device

    def get(self, _device_id):
        return self.device


def test_agent_repository_adds_tenant_predicate():
    session = CaptureSession()
    repo = AgentRepository(session)
    tenant_id = uuid4()
    repo.get(uuid4(), tenant_id=tenant_id)

    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "agents.tenant_id" in sql


def test_enrollment_rejects_cross_tenant_device(monkeypatch):
    tenant_a = uuid4()
    tenant_b = uuid4()
    db = FakeDB()
    service = agent_service.AgentService(db)
    service.devices = FakeDevices(SimpleNamespace(id=uuid4(), tenant_id=tenant_a))
    service.agents = FakeAgents()

    with pytest.raises(HTTPException) as exc:
        service.enroll(
            device_id=uuid4(),
            hostname="CUSTOMER-A-PC",
            version="1.0.0",
            enrollment_secret="secret",
            tenant_id=tenant_b,
        )

    assert exc.value.status_code == 403


def test_enrollment_binds_agent_to_device_tenant(monkeypatch):
    tenant_id = uuid4()
    device_id = uuid4()
    db = FakeDB()
    service = agent_service.AgentService(db)
    service.devices = FakeDevices(SimpleNamespace(id=device_id, tenant_id=tenant_id))
    service.agents = FakeAgents()
    monkeypatch.setattr(agent_service, "hash_password", lambda _secret: "hash")

    agent = service.enroll(
        device_id=device_id,
        hostname="CUSTOMER-PC",
        version="1.0.0",
        enrollment_secret="secret",
    )

    assert isinstance(agent, Agent)
    assert agent.tenant_id == tenant_id
    assert agent.device_id == device_id


def test_enrollment_token_hash_is_not_raw_token(monkeypatch):
    db = FakeDB()
    service = AgentEnrollmentService(db)
    raw, record = service.create(uuid4())

    assert raw
    assert record.token_hash != raw
    assert len(record.token_hash) == 64
