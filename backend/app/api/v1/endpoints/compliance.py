from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.compliance import (
    ComplianceAssessmentCreate,
    ComplianceAssessmentResponse,
    ComplianceAssessmentUpdate,
    ComplianceControlCreate,
    ComplianceControlResponse,
    ComplianceControlUpdate,
    ComplianceEvidenceCreate,
    ComplianceEvidenceResponse,
    ComplianceEvidenceUpdate,
    ComplianceFleetSummary,
    ComplianceFrameworkCreate,
    ComplianceFrameworkResponse,
    ComplianceFrameworkUpdate,
    ComplianceScoreResponse,
    ControlResultBatch,
    ControlResultResponse,
    ControlResultUpsert,
)
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["Compliance"])


def _assessment_resp(row) -> ComplianceAssessmentResponse:
    data = ComplianceAssessmentResponse.model_validate(row)
    if getattr(row, "framework", None):
        data.framework_key = row.framework.framework_key
    return data


def _result_resp(row) -> ControlResultResponse:
    data = ControlResultResponse.model_validate(row)
    if getattr(row, "control", None):
        data.control_ref = row.control.control_id
        data.control_title = row.control.title
    return data


def _score_resp(row) -> ComplianceScoreResponse:
    data = ComplianceScoreResponse.model_validate(row)
    if getattr(row, "framework", None):
        data.framework_key = row.framework.framework_key
        data.display_name = row.framework.display_name
    return data


# ----- Catalog / seed -----------------------------------------------------

@router.get("/catalog")
def get_catalog(db: Session = Depends(get_db)):
    return ComplianceService(db).list_catalog()


@router.post("/frameworks/seed", response_model=list[ComplianceFrameworkResponse], status_code=201)
def seed_frameworks(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    return ComplianceService(db).seed_frameworks(tenant_id=tenant_id)


# ----- Frameworks ---------------------------------------------------------

@router.post("/frameworks", response_model=ComplianceFrameworkResponse, status_code=201)
def create_framework(payload: ComplianceFrameworkCreate, db: Session = Depends(get_db)):
    return ComplianceService(db).create_framework(payload)


@router.get("/frameworks", response_model=list[ComplianceFrameworkResponse])
def list_frameworks(
    enabled_only: bool = False,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return ComplianceService(db).list_frameworks(
        enabled_only=enabled_only, tenant_id=tenant_id
    )


@router.get("/frameworks/{framework_id}", response_model=ComplianceFrameworkResponse)
def get_framework(framework_id: UUID, db: Session = Depends(get_db)):
    row = ComplianceService(db).get_framework(framework_id)
    if not row:
        raise HTTPException(404, "Framework not found")
    return row


@router.patch("/frameworks/{framework_id}", response_model=ComplianceFrameworkResponse)
def update_framework(
    framework_id: UUID, payload: ComplianceFrameworkUpdate, db: Session = Depends(get_db)
):
    row = ComplianceService(db).update_framework(framework_id, payload)
    if not row:
        raise HTTPException(404, "Framework not found")
    return row


# ----- Controls -----------------------------------------------------------

@router.post("/controls", response_model=ComplianceControlResponse, status_code=201)
def create_control(payload: ComplianceControlCreate, db: Session = Depends(get_db)):
    return ComplianceService(db).create_control(payload)


@router.get("/controls", response_model=list[ComplianceControlResponse])
def list_controls(
    framework_id: UUID | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    return ComplianceService(db).list_controls(framework_id=framework_id, category=category)


@router.get("/controls/{control_id}", response_model=ComplianceControlResponse)
def get_control(control_id: UUID, db: Session = Depends(get_db)):
    row = ComplianceService(db).get_control(control_id)
    if not row:
        raise HTTPException(404, "Control not found")
    return row


@router.patch("/controls/{control_id}", response_model=ComplianceControlResponse)
def update_control(
    control_id: UUID, payload: ComplianceControlUpdate, db: Session = Depends(get_db)
):
    row = ComplianceService(db).update_control(control_id, payload)
    if not row:
        raise HTTPException(404, "Control not found")
    return row


# ----- Assessments --------------------------------------------------------

@router.post("/assessments", response_model=ComplianceAssessmentResponse, status_code=201)
def create_assessment(payload: ComplianceAssessmentCreate, db: Session = Depends(get_db)):
    try:
        row = ComplianceService(db).create_assessment(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _assessment_resp(row)


@router.get("/assessments", response_model=list[ComplianceAssessmentResponse])
def list_assessments(
    framework_id: UUID | None = None,
    tenant_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    rows = ComplianceService(db).list_assessments(
        framework_id=framework_id, tenant_id=tenant_id, status=status
    )
    return [_assessment_resp(r) for r in rows]


@router.get("/assessments/{assessment_id}", response_model=ComplianceAssessmentResponse)
def get_assessment(assessment_id: UUID, db: Session = Depends(get_db)):
    row = ComplianceService(db).get_assessment(assessment_id)
    if not row:
        raise HTTPException(404, "Assessment not found")
    return _assessment_resp(row)


@router.patch("/assessments/{assessment_id}", response_model=ComplianceAssessmentResponse)
def update_assessment(
    assessment_id: UUID, payload: ComplianceAssessmentUpdate, db: Session = Depends(get_db)
):
    row = ComplianceService(db).update_assessment(assessment_id, payload)
    if not row:
        raise HTTPException(404, "Assessment not found")
    return _assessment_resp(row)


@router.post("/assessments/{assessment_id}/start", response_model=ComplianceAssessmentResponse)
def start_assessment(assessment_id: UUID, db: Session = Depends(get_db)):
    try:
        row = ComplianceService(db).start_assessment(assessment_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _assessment_resp(row)


@router.post("/assessments/{assessment_id}/complete", response_model=ComplianceAssessmentResponse)
def complete_assessment(assessment_id: UUID, db: Session = Depends(get_db)):
    try:
        row = ComplianceService(db).complete_assessment(assessment_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _assessment_resp(row)


# ----- Control results ----------------------------------------------------

@router.post(
    "/assessments/{assessment_id}/results",
    response_model=list[ControlResultResponse],
    status_code=201,
)
def upsert_results(
    assessment_id: UUID, payload: ControlResultBatch, db: Session = Depends(get_db)
):
    try:
        rows = ComplianceService(db).batch_upsert_results(assessment_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return [_result_resp(r) for r in rows]


@router.get(
    "/assessments/{assessment_id}/results",
    response_model=list[ControlResultResponse],
)
def list_results(assessment_id: UUID, db: Session = Depends(get_db)):
    rows = ComplianceService(db).list_results(assessment_id)
    return [_result_resp(r) for r in rows]


@router.put(
    "/assessments/{assessment_id}/results/{control_id}",
    response_model=ControlResultResponse,
)
def upsert_one_result(
    assessment_id: UUID,
    control_id: UUID,
    payload: ControlResultUpsert,
    db: Session = Depends(get_db),
):
    payload.control_id = control_id
    try:
        rows = ComplianceService(db).batch_upsert_results(
            assessment_id, ControlResultBatch(results=[payload])
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _result_resp(rows[0])


# ----- Evidence -----------------------------------------------------------

@router.post("/evidence", response_model=ComplianceEvidenceResponse, status_code=201)
def create_evidence(payload: ComplianceEvidenceCreate, db: Session = Depends(get_db)):
    return ComplianceService(db).create_evidence(payload)


@router.get("/evidence", response_model=list[ComplianceEvidenceResponse])
def list_evidence(
    control_id: UUID | None = None,
    assessment_id: UUID | None = None,
    tenant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return ComplianceService(db).list_evidence(
        control_id=control_id, assessment_id=assessment_id, tenant_id=tenant_id
    )


@router.get("/evidence/{evidence_id}", response_model=ComplianceEvidenceResponse)
def get_evidence(evidence_id: UUID, db: Session = Depends(get_db)):
    row = ComplianceService(db).get_evidence(evidence_id)
    if not row:
        raise HTTPException(404, "Evidence not found")
    return row


@router.patch("/evidence/{evidence_id}", response_model=ComplianceEvidenceResponse)
def update_evidence(
    evidence_id: UUID, payload: ComplianceEvidenceUpdate, db: Session = Depends(get_db)
):
    row = ComplianceService(db).update_evidence(evidence_id, payload)
    if not row:
        raise HTTPException(404, "Evidence not found")
    return row


# ----- Scores / summary ---------------------------------------------------

@router.post("/scores/compute", response_model=ComplianceScoreResponse)
def compute_score(
    framework_id: UUID,
    tenant_id: UUID | None = None,
    assessment_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    try:
        row = ComplianceService(db).compute_score(
            framework_id, tenant_id=tenant_id, assessment_id=assessment_id
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    scores = ComplianceService(db).list_scores(tenant_id=tenant_id)
    loaded = next((s for s in scores if s.id == row.id), row)
    return _score_resp(loaded)


@router.get("/scores", response_model=list[ComplianceScoreResponse])
def list_scores(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    rows = ComplianceService(db).list_scores(tenant_id=tenant_id)
    return [_score_resp(r) for r in rows]


@router.get("/summary", response_model=ComplianceFleetSummary)
def fleet_summary(tenant_id: UUID | None = None, db: Session = Depends(get_db)):
    return ComplianceService(db).fleet_summary(tenant_id=tenant_id)
