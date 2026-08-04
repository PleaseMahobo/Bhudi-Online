from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import monitoring
from app.core.bootstrap import _bootstrap_metadata_for_engine
from app.database.session import get_db


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/monitoring/azure", {"subscription_id": "sub-123", "resource_types": ["vm", "appservice"]}),
        ("/monitoring/vmware", {"host": "vcsa01.local", "resource_types": ["vm", "datastore"]}),
        ("/monitoring/hyperv", {"host": "hv01.local", "resource_types": ["vm", "host"]}),
        ("/monitoring/dns", {"target": "example.com", "record_type": "A"}),
        ("/monitoring/ping", {"target": "example.com"}),
        ("/monitoring/snmp", {"host": "192.0.2.10", "community": "public"}),
        ("/monitoring/services", {"services": ["ssh", "nginx"]}),
        ("/monitoring/processes", {"processes": ["sshd", "nginx"]}),
        ("/monitoring/ports", {"ports": [22, 80]}),
        ("/monitoring/smart", {"device": "sda"}),
        ("/monitoring/temperature", {"sensors": ["cpu", "gpu"]}),
        ("/monitoring/battery", {"devices": ["laptop-battery"]}),
        ("/monitoring/ups", {"device": "ups-01"}),
        ("/monitoring/bandwidth", {"interfaces": ["eth0"]}),
        ("/monitoring/certificates", {"hosts": ["example.com"]}),
        ("/monitoring/website", {"urls": ["https://example.com"]}),
    ],
)
def test_monitoring_catalog_endpoints_return_health_summary(path: str, payload: dict) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _bootstrap_metadata_for_engine().create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(monitoring.router, prefix="/monitoring")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post(path, json=payload)

    assert response.status_code == 200
    payload_json = response.json()
    assert payload_json["status"] in {"healthy", "warning"}
    assert payload_json["summary"]["resource_count"] >= 1


def test_monitoring_dns_reports_warning_for_invalid_target() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _bootstrap_metadata_for_engine().create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(monitoring.router, prefix="/monitoring")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post("/monitoring/dns", json={"target": "does-not-resolve.invalid", "record_type": "A"})

    assert response.status_code == 200
    payload_json = response.json()
    assert payload_json["status"] == "warning"
    assert payload_json["resources"][0]["status"] == "warning"
