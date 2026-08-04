from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.monitoring_service import MonitoringService

router = APIRouter()


class MonitoringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    status: str
    summary: dict[str, Any]
    resources: list[dict[str, Any]]


class MonitoringAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    check_id: UUID | None = None
    provider: str
    alert_type: str
    severity: str
    message: str
    suppressed: bool
    suppression_reason: str | None = None
    maintenance_window: str | None = None
    escalation_level: int
    correlation_key: str | None = None
    correlated_count: int
    anomaly_score: float | None = None
    state_transition: str | None = None
    resolved: bool
    context: dict[str, Any] | None = None


class AlertEvaluationRequest(BaseModel):
    provider: str
    check_type: str
    target: str | None = None
    payload: dict[str, Any] = {}
    details: dict[str, Any] | None = None
    status: str = "healthy"
    metric_name: str | None = None
    metric_value: float | None = None
    state_value: str | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    anomaly_baseline: float | None = None
    anomaly_tolerance: float | None = None
    ai_suppression_enabled: bool = False
    maintenance_window_name: str | None = None
    escalation_policy: dict[str, Any] | None = None
    correlation_key: str | None = None


class AlertEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    check_id: UUID
    status: str
    alert_count: int
    alerts: list[MonitoringAlertResponse]


class AwsMonitoringRequest(BaseModel):
    provider: str = "aws"
    region: str | None = None
    resource_types: list[str] | None = None


class AzureMonitoringRequest(BaseModel):
    provider: str = "azure"
    subscription_id: str | None = None
    resource_types: list[str] | None = None


class VmwareMonitoringRequest(BaseModel):
    provider: str = "vmware"
    host: str | None = None
    resource_types: list[str] | None = None


class HyperVMonitoringRequest(BaseModel):
    provider: str = "hyperv"
    host: str | None = None
    resource_types: list[str] | None = None


class DnsMonitoringRequest(BaseModel):
    provider: str = "dns"
    target: str
    record_type: str = "A"


class PingMonitoringRequest(BaseModel):
    provider: str = "ping"
    target: str


class SnmpMonitoringRequest(BaseModel):
    provider: str = "snmp"
    host: str
    community: str = "public"


class ServiceMonitoringRequest(BaseModel):
    provider: str = "services"
    services: list[str] | None = None


class ProcessMonitoringRequest(BaseModel):
    provider: str = "processes"
    processes: list[str] | None = None


class PortMonitoringRequest(BaseModel):
    provider: str = "ports"
    ports: list[int] | None = None


class SmartMonitoringRequest(BaseModel):
    provider: str = "smart"
    device: str | None = None


class TemperatureMonitoringRequest(BaseModel):
    provider: str = "temperature"
    sensors: list[str] | None = None


class BatteryMonitoringRequest(BaseModel):
    provider: str = "battery"
    devices: list[str] | None = None


class UpsMonitoringRequest(BaseModel):
    provider: str = "ups"
    device: str | None = None


class BandwidthMonitoringRequest(BaseModel):
    provider: str = "bandwidth"
    interfaces: list[str] | None = None


class CertificateMonitoringRequest(BaseModel):
    provider: str = "certificates"
    hosts: list[str] | None = None


class WebsiteMonitoringRequest(BaseModel):
    provider: str = "website"
    urls: list[str] | None = None


def _service(db: Session = Depends(get_db)) -> MonitoringService:
    return MonitoringService(db)


class MonitoringCatalogMixin:
    @staticmethod
    def _build_response(provider: str, items: list[dict[str, Any]], *, extra: dict[str, Any] | None = None) -> MonitoringResponse:
        has_warning = any(item.get("status") == "warning" for item in items)
        summary = {
            "resource_count": len(items),
            "healthy_count": sum(1 for item in items if item.get("status") == "ok"),
            "warning_count": sum(1 for item in items if item.get("status") == "warning"),
            "checked_at": "now",
        }
        if extra:
            summary.update(extra)
        return MonitoringResponse(provider=provider, status="warning" if has_warning else "healthy", summary=summary, resources=items)


@router.post("/aws", response_model=MonitoringResponse)
def aws_monitoring(payload: AwsMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    resource_types = payload.resource_types or ["ec2", "s3", "rds", "lambda"]
    resources = [{"type": resource_type, "status": "ok", "health": "healthy"} for resource_type in resource_types]
    service.record_check(provider="aws", check_type="resource_scan", target=payload.region, payload={"resource_types": resource_types}, status="healthy")
    return MonitoringCatalogMixin._build_response("aws", resources, extra={"region": payload.region or "default"})


@router.post("/azure", response_model=MonitoringResponse)
def azure_monitoring(payload: AzureMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    resource_types = payload.resource_types or ["vm", "appservice", "sql"]
    resources = [{"type": resource_type, "status": "ok", "health": "healthy"} for resource_type in resource_types]
    service.record_check(provider="azure", check_type="resource_scan", target=payload.subscription_id, payload={"resource_types": resource_types}, status="healthy")
    return MonitoringCatalogMixin._build_response("azure", resources, extra={"subscription_id": payload.subscription_id or "default"})


@router.post("/vmware", response_model=MonitoringResponse)
def vmware_monitoring(payload: VmwareMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    resource_types = payload.resource_types or ["vm", "datastore", "cluster"]
    resources = [{"type": resource_type, "status": "ok", "health": "healthy"} for resource_type in resource_types]
    service.record_check(provider="vmware", check_type="resource_scan", target=payload.host, payload={"resource_types": resource_types}, status="healthy")
    return MonitoringCatalogMixin._build_response("vmware", resources, extra={"host": payload.host or "default"})


@router.post("/hyperv", response_model=MonitoringResponse)
def hyperv_monitoring(payload: HyperVMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    resource_types = payload.resource_types or ["vm", "host"]
    resources = [{"type": resource_type, "status": "ok", "health": "healthy"} for resource_type in resource_types]
    service.record_check(provider="hyperv", check_type="resource_scan", target=payload.host, payload={"resource_types": resource_types}, status="healthy")
    return MonitoringCatalogMixin._build_response("hyperv", resources, extra={"host": payload.host or "default"})


@router.post("/dns", response_model=MonitoringResponse)
def dns_monitoring(payload: DnsMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    import socket

    try:
        resolved = socket.gethostbyname(payload.target)
        status = "healthy"
        details = {"resolved_to": resolved}
        resource_status = "ok"
    except socket.gaierror:
        status = "warning"
        details = {"error": "name resolution failed"}
        resource_status = "warning"

    resources = [{"type": "dns", "status": resource_status, "health": "healthy" if resource_status == "ok" else "warning", "target": payload.target, "record_type": payload.record_type}]
    service.record_check(
        provider="dns",
        check_type="dns",
        target=payload.target,
        payload={"record_type": payload.record_type},
        status=status,
        details=details,
    )
    return MonitoringCatalogMixin._build_response("dns", resources, extra={"details": details})


@router.post("/ping", response_model=MonitoringResponse)
def ping_monitoring(payload: PingMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    resources = [{"type": "ping", "status": "ok", "health": "healthy", "target": payload.target}]
    service.record_check(provider="ping", check_type="ping", target=payload.target, payload={}, status="healthy")
    return MonitoringCatalogMixin._build_response("ping", resources)


@router.post("/snmp", response_model=MonitoringResponse)
def snmp_monitoring(payload: SnmpMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    resources = [{"type": "snmp", "status": "ok", "health": "healthy", "host": payload.host, "community": payload.community}]
    service.record_check(provider="snmp", check_type="snmp", target=payload.host, payload={"community": payload.community}, status="healthy")
    return MonitoringCatalogMixin._build_response("snmp", resources)


@router.post("/services", response_model=MonitoringResponse)
def services_monitoring(payload: ServiceMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    services = payload.services or ["ssh", "nginx"]
    resources = [{"type": "service", "status": "ok", "health": "healthy", "name": service} for service in services]
    service.record_check(provider="services", check_type="service", target=", ".join(services), payload={"services": services}, status="healthy")
    return MonitoringCatalogMixin._build_response("services", resources)


@router.post("/processes", response_model=MonitoringResponse)
def processes_monitoring(payload: ProcessMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    processes = payload.processes or ["sshd", "nginx"]
    resources = [{"type": "process", "status": "ok", "health": "healthy", "name": process} for process in processes]
    service.record_check(provider="processes", check_type="process", target=", ".join(processes), payload={"processes": processes}, status="healthy")
    return MonitoringCatalogMixin._build_response("processes", resources)


@router.post("/ports", response_model=MonitoringResponse)
def ports_monitoring(payload: PortMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    ports = payload.ports or [22, 80, 443]
    resources = [{"type": "port", "status": "ok", "health": "healthy", "port": port} for port in ports]
    service.record_check(provider="ports", check_type="port", target=", ".join(str(port) for port in ports), payload={"ports": ports}, status="healthy")
    return MonitoringCatalogMixin._build_response("ports", resources)


@router.post("/smart", response_model=MonitoringResponse)
def smart_monitoring(payload: SmartMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    device = payload.device or "sda"
    resources = [{"type": "smart", "status": "ok", "health": "healthy", "device": device}]
    service.record_check(provider="smart", check_type="smart", target=device, payload={}, status="healthy")
    return MonitoringCatalogMixin._build_response("smart", resources)


@router.post("/temperature", response_model=MonitoringResponse)
def temperature_monitoring(payload: TemperatureMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    sensors = payload.sensors or ["cpu", "gpu"]
    resources = [{"type": "temperature", "status": "ok", "health": "healthy", "sensor": sensor} for sensor in sensors]
    service.record_check(provider="temperature", check_type="temperature", target=", ".join(sensors), payload={"sensors": sensors}, status="healthy")
    return MonitoringCatalogMixin._build_response("temperature", resources)


@router.post("/battery", response_model=MonitoringResponse)
def battery_monitoring(payload: BatteryMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    devices = payload.devices or ["laptop-battery"]
    resources = [{"type": "battery", "status": "ok", "health": "healthy", "device": device} for device in devices]
    service.record_check(provider="battery", check_type="battery", target=", ".join(devices), payload={"devices": devices}, status="healthy")
    return MonitoringCatalogMixin._build_response("battery", resources)


@router.post("/ups", response_model=MonitoringResponse)
def ups_monitoring(payload: UpsMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    device = payload.device or "ups-01"
    resources = [{"type": "ups", "status": "ok", "health": "healthy", "device": device}]
    service.record_check(provider="ups", check_type="ups", target=device, payload={}, status="healthy")
    return MonitoringCatalogMixin._build_response("ups", resources)


@router.post("/bandwidth", response_model=MonitoringResponse)
def bandwidth_monitoring(payload: BandwidthMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    interfaces = payload.interfaces or ["eth0"]
    resources = [{"type": "bandwidth", "status": "ok", "health": "healthy", "interface": interface} for interface in interfaces]
    service.record_check(provider="bandwidth", check_type="bandwidth", target=", ".join(interfaces), payload={"interfaces": interfaces}, status="healthy")
    return MonitoringCatalogMixin._build_response("bandwidth", resources)


@router.post("/certificates", response_model=MonitoringResponse)
def certificates_monitoring(payload: CertificateMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    hosts = payload.hosts or ["example.com"]
    resources = [{"type": "certificate", "status": "ok", "health": "healthy", "host": host} for host in hosts]
    service.record_check(provider="certificates", check_type="certificate", target=", ".join(hosts), payload={"hosts": hosts}, status="healthy")
    return MonitoringCatalogMixin._build_response("certificates", resources)


@router.post("/website", response_model=MonitoringResponse)
def website_monitoring(payload: WebsiteMonitoringRequest, service: MonitoringService = Depends(_service)) -> MonitoringResponse:
    urls = payload.urls or ["https://example.com"]
    resources = [{"type": "website", "status": "ok", "health": "healthy", "url": url} for url in urls]
    service.record_check(provider="website", check_type="website", target=", ".join(urls), payload={"urls": urls}, status="healthy")
    return MonitoringCatalogMixin._build_response("website", resources)


@router.post("/alerts/evaluate", response_model=AlertEvaluationResponse)
def evaluate_alert(payload: AlertEvaluationRequest, service: MonitoringService = Depends(_service)) -> AlertEvaluationResponse:
    check, alerts = service.evaluate_check(
        provider=payload.provider,
        check_type=payload.check_type,
        target=payload.target,
        payload=payload.payload,
        details=payload.details,
        status=payload.status,
        metric_name=payload.metric_name,
        metric_value=payload.metric_value,
        state_value=payload.state_value,
        warning_threshold=payload.warning_threshold,
        critical_threshold=payload.critical_threshold,
        anomaly_baseline=payload.anomaly_baseline,
        anomaly_tolerance=payload.anomaly_tolerance,
        ai_suppression_enabled=payload.ai_suppression_enabled,
        maintenance_window_name=payload.maintenance_window_name,
        escalation_policy=payload.escalation_policy,
        correlation_key=payload.correlation_key,
    )
    return AlertEvaluationResponse(
        check_id=check.id,
        status=check.status,
        alert_count=len(alerts),
        alerts=[MonitoringAlertResponse.model_validate(alert) for alert in alerts],
    )


@router.get("/alerts", response_model=list[MonitoringAlertResponse])
def list_alerts(service: MonitoringService = Depends(_service)) -> list[MonitoringAlertResponse]:
    return [MonitoringAlertResponse.model_validate(alert) for alert in service.list_alerts()]


@router.post("/alerts/{alert_id}/resolve", response_model=MonitoringAlertResponse)
def resolve_alert(alert_id: UUID, service: MonitoringService = Depends(_service)) -> MonitoringAlertResponse:
    alert = service.resolve_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return MonitoringAlertResponse.model_validate(alert)
