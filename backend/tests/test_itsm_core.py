from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import itsm
from app.core.bootstrap import _bootstrap_metadata_for_engine
from app.core.dependencies import get_current_user
from app.database.session import get_db


TENANT_A = "00000000-0000-0000-0000-0000000000a1"
TENANT_B = "00000000-0000-0000-0000-0000000000b1"


def _client(tenant_id: str):
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _bootstrap_metadata_for_engine().create_all(bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(itsm.router, prefix="/api")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000099"),
        tenant_id=UUID(tenant_id),
        email="technician@example.test",
        active=True,
    )
    return TestClient(app)


def test_ticket_lifecycle_search_and_status_note() -> None:
    client = _client(TENANT_A)

    create = client.post(
        "/api/itsm/tickets",
        json={
            "title": "Printer offline",
            "description": "Kyocera is unreachable",
            "ticket_type": "incident",
            "priority": "high",
            "requester": "user@example.test",
            "sla_resolve_minutes": 60,
        },
    )
    assert create.status_code == 201, create.text
    ticket = create.json()
    assert ticket["number"].startswith("INC-")
    assert ticket["tenant_id"] == TENANT_A

    search = client.get("/api/itsm/tickets", params={"q": "Kyocera"})
    assert search.status_code == 200
    assert [row["id"] for row in search.json()] == [ticket["id"]]

    transition = client.post(
        f"/api/itsm/tickets/{ticket['id']}/status",
        json={"status": "resolved", "resolution": "Printer recovered"},
    )
    assert transition.status_code == 200, transition.text
    assert transition.json()["status"] == "resolved"
    assert transition.json()["resolved_at"] is not None

    notes = client.get(f"/api/itsm/tickets/{ticket['id']}/notes")
    assert notes.status_code == 200
    assert any("Status changed" in note["body"] for note in notes.json())


def test_ticket_tenant_isolation() -> None:
    client_a = _client(TENANT_A)
    create = client_a.post(
        "/api/itsm/tickets",
        json={"title": "Tenant A ticket", "ticket_type": "incident", "priority": "medium"},
    )
    assert create.status_code == 201, create.text
    ticket_id = create.json()["id"]

    client_b = _client(TENANT_B)
    response = client_b.get(f"/api/itsm/tickets/{ticket_id}")
    assert response.status_code == 404


def test_invalid_status_is_rejected() -> None:
    client = _client(TENANT_A)
    response = client.post(
        "/api/itsm/tickets",
        json={"title": "Invalid", "ticket_type": "incident", "status": "bogus"},
    )
    assert response.status_code == 400
