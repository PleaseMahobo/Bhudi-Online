from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import monitoring
from app.core.bootstrap import _bootstrap_metadata_for_engine
from app.database.session import get_db


def test_aws_monitoring_endpoint_reports_summary() -> None:
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

    response = client.post(
        "/monitoring/aws",
        json={"region": "us-east-1", "resource_types": ["ec2", "s3"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "aws"
    assert payload["status"] == "healthy"
    assert payload["summary"]["resource_count"] == 2
    assert len(payload["resources"]) == 2
