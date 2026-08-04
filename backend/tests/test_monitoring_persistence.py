from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import monitoring
from app.core.bootstrap import _bootstrap_metadata_for_engine
from app.database.session import get_db
from app.models.device_management import MaintenanceWindow
from app.models.monitoring import MonitoringAlert, MonitoringCheck


def test_monitoring_checks_and_alerts_are_persisted() -> None:
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

    response = client.post("/monitoring/ping", json={"target": "example.com"})
    assert response.status_code == 200

    db = TestingSessionLocal()
    checks = db.query(MonitoringCheck).all()
    alerts = db.query(MonitoringAlert).all()
    db.close()

    assert len(checks) >= 1
    assert len(alerts) == 0


def test_alert_engine_supports_threshold_state_anomaly_and_correlation() -> None:
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

    baseline_response = client.post(
        "/monitoring/alerts/evaluate",
        json={
            "provider": "infrastructure",
            "check_type": "cpu",
            "target": "server-01",
            "metric_name": "cpu_percent",
            "metric_value": 22,
            "state_value": "up",
            "warning_threshold": 70,
            "critical_threshold": 90,
            "anomaly_tolerance": 20,
            "correlation_key": "site-a/core",
            "escalation_policy": {"levels": [{"repeat_count": 2, "severity": "critical"}]},
        },
    )

    assert baseline_response.status_code == 200
    assert baseline_response.json()["alert_count"] == 0

    triggered_response = client.post(
        "/monitoring/alerts/evaluate",
        json={
            "provider": "infrastructure",
            "check_type": "cpu",
            "target": "server-01",
            "metric_name": "cpu_percent",
            "metric_value": 96,
            "state_value": "down",
            "warning_threshold": 70,
            "critical_threshold": 90,
            "anomaly_tolerance": 20,
            "correlation_key": "site-a/core",
            "escalation_policy": {"levels": [{"repeat_count": 2, "severity": "critical"}]},
        },
    )

    assert triggered_response.status_code == 200
    payload = triggered_response.json()
    assert payload["status"] == "critical"
    assert payload["alert_count"] == 3

    alert_types = {alert["alert_type"] for alert in payload["alerts"]}
    assert "threshold" in alert_types
    assert "state_change" in alert_types
    assert "anomaly" in alert_types
    assert any(alert["correlated_count"] >= 1 for alert in payload["alerts"])
    assert any(alert["escalation_level"] >= 1 for alert in payload["alerts"])


def test_alert_engine_supports_ai_and_maintenance_suppression() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _bootstrap_metadata_for_engine().create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(
        MaintenanceWindow(
            name="patch-window",
            start="2026-08-04T00:00:00+00:00",
            end="2026-08-05T00:00:00+00:00",
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(monitoring.router, prefix="/monitoring")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    first_response = client.post(
        "/monitoring/alerts/evaluate",
        json={
            "provider": "website",
            "check_type": "latency",
            "target": "https://example.com",
            "metric_name": "latency_ms",
            "metric_value": 480,
            "warning_threshold": 300,
            "critical_threshold": 450,
            "ai_suppression_enabled": True,
            "correlation_key": "web/example",
        },
    )
    assert first_response.status_code == 200
    first_alert = first_response.json()["alerts"][0]
    assert first_alert["suppressed"] is False

    suppressed_response = client.post(
        "/monitoring/alerts/evaluate",
        json={
            "provider": "website",
            "check_type": "latency",
            "target": "https://example.com",
            "metric_name": "latency_ms",
            "metric_value": 490,
            "warning_threshold": 300,
            "critical_threshold": 450,
            "ai_suppression_enabled": True,
            "correlation_key": "web/example",
        },
    )
    assert suppressed_response.status_code == 200
    suppressed_alert = suppressed_response.json()["alerts"][0]
    assert suppressed_alert["suppressed"] is True
    assert suppressed_alert["suppression_reason"] == "ai_similarity_suppression"

    maintenance_response = client.post(
        "/monitoring/alerts/evaluate",
        json={
            "provider": "infrastructure",
            "check_type": "disk",
            "target": "server-02",
            "metric_name": "disk_percent",
            "metric_value": 95,
            "warning_threshold": 80,
            "critical_threshold": 90,
            "maintenance_window_name": "patch-window",
        },
    )
    assert maintenance_response.status_code == 200
    maintenance_alert = maintenance_response.json()["alerts"][0]
    assert maintenance_alert["suppressed"] is True
    assert maintenance_alert["suppression_reason"] == "maintenance_window_active"
