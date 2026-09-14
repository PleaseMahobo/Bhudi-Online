from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.endpoint_security import (
    AgentIngestPayload,
    EndpointSecurityAgentCreate,
    EndpointSecurityAgentResponse,
    EndpointSecurityAgentUpdate,
    EndpointSecurityScoreResponse,
    FindingIngestPayload,
    OrgSecurityScoreResponse,
    SecurityFindingCreate,
    SecurityFindingResponse,
    SecurityFindingUpdate,
    SecurityProviderCreate,
    SecurityProviderResponse,
    SecurityProviderUpdate,
)
from app.services.endpoint_security_service import (
    PROVIDER_CATALOG,
    EndpointSecurityService,
)
from app.services.vendor_security_connectors import CONNECTORS, sync_all_enabled, sync_provider

router = APIRouter(prefix="/endpoint-security", tags=["Endpoint Security"])


def _agent_response(row) -> EndpointSecurityAgentResponse:
    data = EndpointSecurityAgentResponse.model_validate(row)
    if row.provider:
        data.provider_key = row.provider.provider_key
        data.provider_name = row.provider.display_name
    return data


def _finding_response(row) -> SecurityFindingResponse:
    data = SecurityFindingResponse.model_validate(row)
    if row.provider:
        data.provider_key = row.provider.provider_key
    return data


# ---------- Catalog / providers ----------

@router.get("/catalog")
def list_catalog():
    return PROVIDER_CATALOG


@router.post(
    "/providers/seed",
    response_model=list[SecurityProviderResponse],
    status_code=status.HTTP_201_CREATED,
)
def seed_providers(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    return EndpointSecurityService(db).seed_default_providers(tenant_id=tenant_id)


@router.post(
    "/providers",
    response_model=SecurityProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_provider(payload: SecurityProviderCreate, db: Session = Depends(get_db)):
    return EndpointSecurityService(db).create_provider(payload)


@router.get("/providers", response_model=list[SecurityProviderResponse])
def list_providers(
    enabled_only: bool = False,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return EndpointSecurityService(db).list_providers(
        enabled_only=enabled_only, tenant_id=tenant_id
    )


@router.get("/providers/{provider_id}", response_model=SecurityProviderResponse)
def get_provider(provider_id: UUID, db: Session = Depends(get_db)):
    row = EndpointSecurityService(db).get_provider(provider_id)
    if not row:
        raise HTTPException(404, "Provider not found")
    return row


@router.patch("/providers/{provider_id}", response_model=SecurityProviderResponse)
def update_provider(
    provider_id: UUID, payload: SecurityProviderUpdate, db: Session = Depends(get_db)
):
    row = EndpointSecurityService(db).update_provider(provider_id, payload)
    if not row:
        raise HTTPException(404, "Provider not found")
    return row


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: UUID, db: Session = Depends(get_db)):
    if not EndpointSecurityService(db).delete_provider(provider_id):
        raise HTTPException(404, "Provider not found")


@router.post("/providers/{provider_id}/sync")
def sync_provider_cloud(provider_id: UUID, db: Session = Depends(get_db)):
    """Pull agents/findings from the vendor cloud API (if connector exists)."""
    row = EndpointSecurityService(db).get_provider(provider_id)
    if not row:
        raise HTTPException(404, "Provider not found")
    result = sync_provider(db, row)
    return result.to_dict()


@router.post("/providers/sync-all")
def sync_all_providers(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    """Run cloud sync for every enabled provider that has a connector."""
    return {"results": sync_all_enabled(db, tenant_id=tenant_id)}


@router.get("/connectors")
def list_cloud_connectors():
    """Which provider_keys have a cloud API connector implemented."""
    return {
        "connectors": sorted(CONNECTORS.keys()),
        "note": "Agent-side detection works for all catalog products; cloud sync is optional.",
    }


# ---------- Agents ----------

@router.post(
    "/agents",
    response_model=EndpointSecurityAgentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent(payload: EndpointSecurityAgentCreate, db: Session = Depends(get_db)):
    try:
        row = EndpointSecurityService(db).create_agent(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    agents = EndpointSecurityService(db).list_agents()
    row = next((a for a in agents if a.id == row.id), row)
    return _agent_response(row)


@router.get("/agents", response_model=list[EndpointSecurityAgentResponse])
def list_agents(
    device_id: UUID | None = None,
    provider_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    rows = EndpointSecurityService(db).list_agents(
        device_id=device_id, provider_id=provider_id, status=status
    )
    return [_agent_response(r) for r in rows]


@router.patch("/agents/{agent_id}", response_model=EndpointSecurityAgentResponse)
def update_agent(
    agent_id: UUID,
    payload: EndpointSecurityAgentUpdate,
    db: Session = Depends(get_db),
):
    row = EndpointSecurityService(db).update_agent(agent_id, payload)
    if not row:
        raise HTTPException(404, "Agent not found")
    agents = EndpointSecurityService(db).list_agents()
    row = next((a for a in agents if a.id == row.id), row)
    return _agent_response(row)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: UUID, db: Session = Depends(get_db)):
    if not EndpointSecurityService(db).delete_agent(agent_id):
        raise HTTPException(404, "Agent not found")


@router.post(
    "/ingest/agent",
    response_model=EndpointSecurityAgentResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_agent(payload: AgentIngestPayload, db: Session = Depends(get_db)):
    try:
        row = EndpointSecurityService(db).ingest_agent(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    agents = EndpointSecurityService(db).list_agents()
    row = next((a for a in agents if a.id == row.id), row)
    return _agent_response(row)


# ---------- Findings ----------

@router.post(
    "/findings",
    response_model=SecurityFindingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_finding(payload: SecurityFindingCreate, db: Session = Depends(get_db)):
    try:
        row = EndpointSecurityService(db).create_finding(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    findings = EndpointSecurityService(db).list_findings()
    row = next((f for f in findings if f.id == row.id), row)
    return _finding_response(row)


@router.get("/findings", response_model=list[SecurityFindingResponse])
def list_findings(
    device_id: UUID | None = None,
    provider_id: UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
):
    rows = EndpointSecurityService(db).list_findings(
        device_id=device_id,
        provider_id=provider_id,
        status=status,
        severity=severity,
    )
    return [_finding_response(r) for r in rows]


@router.patch("/findings/{finding_id}", response_model=SecurityFindingResponse)
def update_finding(
    finding_id: UUID,
    payload: SecurityFindingUpdate,
    db: Session = Depends(get_db),
):
    row = EndpointSecurityService(db).update_finding(finding_id, payload)
    if not row:
        raise HTTPException(404, "Finding not found")
    findings = EndpointSecurityService(db).list_findings()
    row = next((f for f in findings if f.id == row.id), row)
    return _finding_response(row)


@router.delete("/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_finding(finding_id: UUID, db: Session = Depends(get_db)):
    if not EndpointSecurityService(db).delete_finding(finding_id):
        raise HTTPException(404, "Finding not found")


@router.post(
    "/ingest/finding",
    response_model=SecurityFindingResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_finding(payload: FindingIngestPayload, db: Session = Depends(get_db)):
    try:
        row = EndpointSecurityService(db).ingest_finding(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    findings = EndpointSecurityService(db).list_findings()
    row = next((f for f in findings if f.id == row.id), row)
    return _finding_response(row)


# ---------- Security scores ----------

@router.get("/scores/org", response_model=OrgSecurityScoreResponse)
def org_security_score(db: Session = Depends(get_db)):
    return EndpointSecurityService(db).org_score()


@router.get("/scores", response_model=list[EndpointSecurityScoreResponse])
def list_scores(min_score: int | None = None, db: Session = Depends(get_db)):
    return EndpointSecurityService(db).list_scores(min_score=min_score)


@router.get("/scores/{device_id}", response_model=EndpointSecurityScoreResponse)
def get_device_score(device_id: UUID, db: Session = Depends(get_db)):
    row = EndpointSecurityService(db).get_device_score(device_id)
    if not row:
        row = EndpointSecurityService(db).compute_device_score(device_id)
    return row


@router.post("/scores/{device_id}/recompute", response_model=EndpointSecurityScoreResponse)
def recompute_device_score(device_id: UUID, db: Session = Depends(get_db)):
    return EndpointSecurityService(db).compute_device_score(device_id)


@router.post("/scores/recompute-all")
def recompute_all_scores(db: Session = Depends(get_db)):
    count = EndpointSecurityService(db).recompute_all_scores()
    return {"devices_scored": count}


# ---------- Fleet matrix ----------

@router.get("/matrix")
def security_matrix(
    device_id: UUID | None = None,
    hostname: str | None = None,
    db: Session = Depends(get_db),
):
    svc = EndpointSecurityService(db)
    svc.seed_default_providers()

    agents = svc.list_agents(device_id=device_id)
    if hostname:
        agents = [a for a in agents if (a.hostname or "").lower() == hostname.lower()]

    findings = svc.list_findings(device_id=device_id)
    open_statuses = {"open", "investigating", "contained"}

    threat_map: dict[tuple, dict[str, int]] = {}
    for f in findings:
        if f.status not in open_statuses:
            continue
        key = (str(f.device_id) if f.device_id else None, (f.hostname or "").lower(), str(f.provider_id))
        bucket = threat_map.setdefault(key, {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0})
        sev = (f.severity or "medium").lower()
        if sev in bucket:
            bucket[sev] += 1
        bucket["total"] += 1

    rows = []
    for a in agents:
        key = (str(a.device_id) if a.device_id else None, (a.hostname or "").lower(), str(a.provider_id))
        threats = threat_map.get(key, {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0})

        status = a.status or "unknown"
        if status == "healthy":
            matrix_status = "protected"
        elif status in {"degraded", "offline"}:
            matrix_status = "at_risk"
        elif status == "not_installed":
            matrix_status = "not_installed"
        else:
            matrix_status = status

        if a.definitions_up_to_date is False and matrix_status == "protected":
            matrix_status = "outdated"

        rows.append(
            {
                "device_id": str(a.device_id) if a.device_id else None,
                "hostname": a.hostname,
                "provider_key": a.provider.provider_key if a.provider else None,
                "product_name": a.provider.display_name if a.provider else None,
                "installed": status != "not_installed",
                "version": a.agent_version,
                "status": matrix_status,
                "raw_status": status,
                "real_time_protection": a.real_time_protection,
                "definitions_up_to_date": a.definitions_up_to_date,
                "last_scan_at": a.last_scan_at.isoformat() if a.last_scan_at else None,
                "last_seen_at": a.last_seen_at.isoformat() if a.last_seen_at else None,
                "threats_found": threats["total"],
                "threats_critical": threats["critical"],
                "threats_high": threats["high"],
                "external_agent_id": a.external_agent_id,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
        )

    priority = {p["provider_key"]: i for i, p in enumerate(PROVIDER_CATALOG)}
    rows.sort(key=lambda r: ((r.get("hostname") or "").lower(), priority.get(r.get("provider_key") or "", 99)))

    from datetime import datetime, timezone

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "products": PROVIDER_CATALOG,
        "rows": rows,
    }
