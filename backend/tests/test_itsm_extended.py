from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import itsm_extended
from app.core.bootstrap import _bootstrap_metadata_for_engine
from app.core.dependencies import get_current_user
from app.database.session import get_db

TENANT = UUID("00000000-0000-0000-0000-0000000000a1")
USER = SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000099"), tenant_id=TENANT, email="tech@example.test", active=True)


def client():
    engine = create_engine("sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _bootstrap_metadata_for_engine().create_all(bind=engine)
    def override_db():
        db = Session()
        try: yield db
        finally: db.close()
    app = FastAPI(); app.include_router(itsm_extended.router, prefix="/api")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: USER
    return TestClient(app)


def test_sla_group_summary_and_attachments():
    c = client()
    assert c.post("/api/itsm/sla-policies", json={"name":"High","priority":"high","response_minutes":15,"resolve_minutes":60}).status_code == 201
    assert c.post("/api/itsm/assignment-groups", json={"name":"Service Desk"}).status_code == 201
    ticket = c.post("/api/itsm/intake", json={"title":"VPN down","priority":"high","tenant_id":str(TENANT)}).json()
    assert ticket["number"].startswith("INC-")
    assert ticket["sla_response_minutes"] == 15
    attachment = c.post(f"/api/itsm/tickets/{ticket['id']}/attachments", json={"filename":"log.txt","content_type":"text/plain","storage_key":"tickets/log.txt","size_bytes":42})
    assert attachment.status_code == 201
    history = c.get(f"/api/itsm/tickets/{ticket['id']}/history")
    assert history.status_code == 200
    summary = c.get("/api/itsm/summary").json()
    assert summary["total"] == 1
    assert summary["open"] == 1


def test_tenant_mismatch_is_rejected():
    c = client()
    other = "00000000-0000-0000-0000-0000000000b1"
    response = c.post("/api/itsm/intake", json={"title":"cross tenant","tenant_id":other})
    assert response.status_code == 403
