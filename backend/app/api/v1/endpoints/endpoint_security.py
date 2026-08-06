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
from app.services.endpoint_security_service import EndpointSecurityService

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
    """Supported security products for Phase 12."""
    return EndpointSecurityService(None).list_catalog()  # type: ignore[arg-type]


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
    # reload with provider
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
def list_scores(
    min_score: int | None = None, db: Session = Depends(get_db)
):
    return EndpointSecurityService(db).list_scores(min_score=min_score)


@router.get("/scores/{device_id}", response_model=EndpointSecurityScoreResponse)
def get_device_score(device_id: UUID, db: Session = Depends(get_db)):
    row = EndpointSecurityService(db).get_device_score(device_id)
    if not row:
        # compute on demand
        row = EndpointSecurityService(db).compute_device_score(device_id)
    return row


@router.post(
    "/scores/{device_id}/recompute",
    response_model=EndpointSecurityScoreResponse,
)
def recompute_device_score(device_id: UUID, db: Session = Depends(get_db)):
    return EndpointSecurityService(db).compute_device_score(device_id)


@router.post("/scores/recompute-all")
def recompute_all_scores(db: Session = Depends(get_db)):
    count = EndpointSecurityService(db).recompute_all_scores()
    return {"devices_scored": count}
