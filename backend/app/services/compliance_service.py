from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.compliance import (
    COMPLIANCE_FRAMEWORKS,
    FRAMEWORK_CATALOG,
    ComplianceAssessment,
    ComplianceControl,
    ComplianceEvidence,
    ComplianceFramework,
    ComplianceScore,
    ControlResult,
)
from app.schemas.compliance import (
    ComplianceAssessmentCreate,
    ComplianceAssessmentUpdate,
    ComplianceControlCreate,
    ComplianceControlUpdate,
    ComplianceEvidenceCreate,
    ComplianceEvidenceUpdate,
    ComplianceFleetSummary,
    ComplianceFrameworkCreate,
    ComplianceFrameworkUpdate,
    ControlResultBatch,
    ControlResultUpsert,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _grade(score: float | int | None) -> str:
    if score is None:
        return "F"
    s = float(score)
    if s >= 90:
        return "A"
    if s >= 80:
        return "B"
    if s >= 70:
        return "C"
    if s >= 60:
        return "D"
    return "F"


class ComplianceService:
    """Production compliance service for CIS / ISO27001 / PCI / HIPAA / GDPR / NIST / SOC2."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ----- Catalog / seed -------------------------------------------------

    def list_catalog(self) -> list[dict[str, str]]:
        return list(FRAMEWORK_CATALOG)

    def seed_frameworks(self, tenant_id: UUID | None = None) -> list[ComplianceFramework]:
        created: list[ComplianceFramework] = []
        for item in FRAMEWORK_CATALOG:
            existing = (
                self.db.query(ComplianceFramework)
                .filter(
                    ComplianceFramework.framework_key == item["framework_key"],
                    ComplianceFramework.tenant_id == tenant_id,
                )
                .first()
            )
            if existing:
                created.append(existing)
                continue
            row = ComplianceFramework(
                tenant_id=tenant_id,
                framework_key=item["framework_key"],
                display_name=item["display_name"],
                version=item.get("version"),
                enabled=True,
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for r in created:
            self.db.refresh(r)
        return created

    # ----- Frameworks -----------------------------------------------------

    def create_framework(self, payload: ComplianceFrameworkCreate) -> ComplianceFramework:
        row = ComplianceFramework(**payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_frameworks(
        self, enabled_only: bool = False, tenant_id: UUID | None = None
    ) -> list[ComplianceFramework]:
        q = self.db.query(ComplianceFramework)
        if enabled_only:
            q = q.filter(ComplianceFramework.enabled.is_(True))
        if tenant_id is not None:
            q = q.filter(ComplianceFramework.tenant_id == tenant_id)
        return q.order_by(ComplianceFramework.framework_key).all()

    def get_framework(self, framework_id: UUID) -> ComplianceFramework | None:
        return self.db.get(ComplianceFramework, framework_id)

    def update_framework(
        self, framework_id: UUID, payload: ComplianceFrameworkUpdate
    ) -> ComplianceFramework | None:
        row = self.get_framework(framework_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_framework(self, framework_id: UUID) -> bool:
        row = self.get_framework(framework_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ----- Controls -------------------------------------------------------

    def create_control(self, payload: ComplianceControlCreate) -> ComplianceControl:
        row = ComplianceControl(**payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_controls(
        self, framework_id: UUID | None = None, category: str | None = None
    ) -> list[ComplianceControl]:
        q = self.db.query(ComplianceControl)
        if framework_id:
            q = q.filter(ComplianceControl.framework_id == framework_id)
        if category:
            q = q.filter(ComplianceControl.category == category)
        return q.order_by(ComplianceControl.control_id).all()

    def get_control(self, control_id: UUID) -> ComplianceControl | None:
        return self.db.get(ComplianceControl, control_id)

    def update_control(
        self, control_id: UUID, payload: ComplianceControlUpdate
    ) -> ComplianceControl | None:
        row = self.get_control(control_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_control(self, control_id: UUID) -> bool:
        row = self.get_control(control_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ----- Assessments ----------------------------------------------------

    def create_assessment(
        self, payload: ComplianceAssessmentCreate
    ) -> ComplianceAssessment:
        fw = self.get_framework(payload.framework_id)
        if not fw:
            raise ValueError("Framework not found")
        controls = self.list_controls(framework_id=payload.framework_id)
        row = ComplianceAssessment(
            framework_id=payload.framework_id,
            tenant_id=payload.tenant_id,
            name=payload.name,
            triggered_by=payload.triggered_by,
            total_controls=len(controls),
            not_assessed=len(controls),
            status="pending",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        if payload.auto_start:
            self.start_assessment(row.id)
            self.db.refresh(row)
        return row

    def list_assessments(
        self,
        framework_id: UUID | None = None,
        tenant_id: UUID | None = None,
        status: str | None = None,
    ) -> list[ComplianceAssessment]:
        q = self.db.query(ComplianceAssessment).options(
            joinedload(ComplianceAssessment.framework)
        )
        if framework_id:
            q = q.filter(ComplianceAssessment.framework_id == framework_id)
        if tenant_id:
            q = q.filter(ComplianceAssessment.tenant_id == tenant_id)
        if status:
            q = q.filter(ComplianceAssessment.status == status)
        return q.order_by(ComplianceAssessment.created_at.desc()).all()

    def get_assessment(self, assessment_id: UUID) -> ComplianceAssessment | None:
        return (
            self.db.query(ComplianceAssessment)
            .options(joinedload(ComplianceAssessment.framework))
            .filter(ComplianceAssessment.id == assessment_id)
            .first()
        )

    def start_assessment(self, assessment_id: UUID) -> ComplianceAssessment | None:
        row = self.get_assessment(assessment_id)
        if not row:
            return None
        if row.status not in ("pending", "failed"):
            raise ValueError(f"Cannot start assessment in status {row.status}")
        row.status = "in_progress"
        row.started_at = _utcnow()
        row.error_message = None
        self.db.commit()
        self.db.refresh(row)
        return row

    def complete_assessment(
        self, assessment_id: UUID
    ) -> ComplianceAssessment | None:
        row = self.get_assessment(assessment_id)
        if not row:
            return None
        results = self.list_results(assessment_id)
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        na = sum(1 for r in results if r.status == "not_applicable")
        partial = sum(1 for r in results if r.status == "partial")
        assessed = passed + failed + na + partial
        not_assessed = max(0, row.total_controls - assessed)

        denom = passed + failed + partial
        score = round(100.0 * passed / denom, 1) if denom else None

        row.passed = passed
        row.failed = failed
        row.not_applicable = na
        row.not_assessed = not_assessed
        row.score = score
        row.grade = _grade(score)
        row.status = "completed"
        row.finished_at = _utcnow()
        row.summary = {
            "passed": passed,
            "failed": failed,
            "not_applicable": na,
            "partial": partial,
            "not_assessed": not_assessed,
        }
        self.db.commit()
        self.db.refresh(row)

        # Auto-compute posture score
        try:
            self.compute_score(
                row.framework_id, tenant_id=row.tenant_id, assessment_id=row.id
            )
        except Exception:
            pass
        return row

    def update_assessment(
        self, assessment_id: UUID, payload: ComplianceAssessmentUpdate
    ) -> ComplianceAssessment | None:
        row = self.get_assessment(assessment_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_assessment(self, assessment_id: UUID) -> bool:
        row = self.get_assessment(assessment_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ----- Control results ------------------------------------------------

    def list_results(self, assessment_id: UUID) -> list[ControlResult]:
        return (
            self.db.query(ControlResult)
            .options(joinedload(ControlResult.control))
            .filter(ControlResult.assessment_id == assessment_id)
            .all()
        )

    def upsert_result(
        self, assessment_id: UUID, payload: ControlResultUpsert
    ) -> ControlResult:
        existing = (
            self.db.query(ControlResult)
            .filter(
                ControlResult.assessment_id == assessment_id,
                ControlResult.control_id == payload.control_id,
            )
            .first()
        )
        data = payload.model_dump()
        data["assessed_at"] = _utcnow()
        if existing:
            for k, v in data.items():
                if k != "control_id":
                    setattr(existing, k, v)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        row = ControlResult(assessment_id=assessment_id, **data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def batch_upsert_results(
        self, assessment_id: UUID, payload: ControlResultBatch
    ) -> list[ControlResult]:
        if not self.get_assessment(assessment_id):
            raise ValueError("Assessment not found")
        out: list[ControlResult] = []
        for item in payload.results:
            out.append(self.upsert_result(assessment_id, item))
        return out

    # ----- Evidence -------------------------------------------------------

    def create_evidence(self, payload: ComplianceEvidenceCreate) -> ComplianceEvidence:
        data = payload.model_dump()
        meta = data.pop("metadata", None)
        row = ComplianceEvidence(**data, metadata_json=meta)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_evidence(
        self,
        control_id: UUID | None = None,
        assessment_id: UUID | None = None,
        tenant_id: UUID | None = None,
    ) -> list[ComplianceEvidence]:
        q = self.db.query(ComplianceEvidence)
        if control_id:
            q = q.filter(ComplianceEvidence.control_id == control_id)
        if assessment_id:
            q = q.filter(ComplianceEvidence.assessment_id == assessment_id)
        if tenant_id:
            q = q.filter(ComplianceEvidence.tenant_id == tenant_id)
        return q.order_by(ComplianceEvidence.collected_at.desc()).all()

    def get_evidence(self, evidence_id: UUID) -> ComplianceEvidence | None:
        return self.db.get(ComplianceEvidence, evidence_id)

    def update_evidence(
        self, evidence_id: UUID, payload: ComplianceEvidenceUpdate
    ) -> ComplianceEvidence | None:
        row = self.get_evidence(evidence_id)
        if not row:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "metadata" in data:
            row.metadata_json = data.pop("metadata")
        for k, v in data.items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_evidence(self, evidence_id: UUID) -> bool:
        row = self.get_evidence(evidence_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def expire_stale_evidence(self) -> int:
        now = _utcnow()
        rows = (
            self.db.query(ComplianceEvidence)
            .filter(
                ComplianceEvidence.expires_at.isnot(None),
                ComplianceEvidence.expires_at < now,
                ComplianceEvidence.status == "valid",
            )
            .all()
        )
        for r in rows:
            r.status = "expired"
        self.db.commit()
        return len(rows)

    # ----- Scoring --------------------------------------------------------

    def compute_score(
        self,
        framework_id: UUID,
        tenant_id: UUID | None = None,
        assessment_id: UUID | None = None,
    ) -> ComplianceScore:
        fw = self.get_framework(framework_id)
        if not fw:
            raise ValueError("Framework not found")

        if assessment_id:
            assessment = self.get_assessment(assessment_id)
        else:
            q = (
                self.db.query(ComplianceAssessment)
                .filter(
                    ComplianceAssessment.framework_id == framework_id,
                    ComplianceAssessment.status == "completed",
                )
                .order_by(ComplianceAssessment.finished_at.desc())
            )
            if tenant_id:
                q = q.filter(ComplianceAssessment.tenant_id == tenant_id)
            assessment = q.first()

        passed = failed = total = 0
        score_val = 0
        if assessment:
            passed = assessment.passed or 0
            failed = assessment.failed or 0
            total = assessment.total_controls or 0
            score_val = int(round(assessment.score or 0))

        evidence_q = self.db.query(ComplianceEvidence).filter(
            ComplianceEvidence.status == "valid"
        )
        if tenant_id:
            evidence_q = evidence_q.filter(ComplianceEvidence.tenant_id == tenant_id)
        # count evidence linked to controls of this framework
        control_ids = [
            c.id for c in self.list_controls(framework_id=framework_id)
        ]
        if control_ids:
            evidence_q = evidence_q.filter(
                ComplianceEvidence.control_id.in_(control_ids)
            )
        evidence_count = evidence_q.count()

        factors = {
            "assessment_score": score_val,
            "evidence_bonus": min(10, evidence_count // 5),
            "coverage": round(100.0 * (passed + failed) / total, 1) if total else 0,
        }
        final = min(100, score_val + factors["evidence_bonus"])

        existing = (
            self.db.query(ComplianceScore)
            .filter(
                ComplianceScore.framework_id == framework_id,
                ComplianceScore.tenant_id == tenant_id,
            )
            .first()
        )
        if existing:
            existing.score = final
            existing.grade = _grade(final)
            existing.factors = factors
            existing.controls_passed = passed
            existing.controls_failed = failed
            existing.controls_total = total
            existing.evidence_count = evidence_count
            existing.last_assessment_id = assessment.id if assessment else None
            existing.computed_at = _utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = ComplianceScore(
            framework_id=framework_id,
            tenant_id=tenant_id,
            score=final,
            grade=_grade(final),
            factors=factors,
            controls_passed=passed,
            controls_failed=failed,
            controls_total=total,
            evidence_count=evidence_count,
            last_assessment_id=assessment.id if assessment else None,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_scores(
        self, tenant_id: UUID | None = None
    ) -> list[ComplianceScore]:
        q = self.db.query(ComplianceScore).options(
            joinedload(ComplianceScore.framework)
        )
        if tenant_id is not None:
            q = q.filter(ComplianceScore.tenant_id == tenant_id)
        return q.order_by(ComplianceScore.computed_at.desc()).all()

    def fleet_summary(
        self, tenant_id: UUID | None = None
    ) -> ComplianceFleetSummary:
        frameworks = self.list_frameworks(enabled_only=True, tenant_id=tenant_id)
        controls_total = 0
        by_fw: list[dict[str, Any]] = []
        for fw in frameworks:
            ctrls = self.list_controls(framework_id=fw.id)
            controls_total += len(ctrls)
            scores = [
                s
                for s in self.list_scores(tenant_id=tenant_id)
                if s.framework_id == fw.id
            ]
            sc = scores[0] if scores else None
            by_fw.append(
                {
                    "framework_key": fw.framework_key,
                    "display_name": fw.display_name,
                    "controls": len(ctrls),
                    "score": sc.score if sc else None,
                    "grade": sc.grade if sc else None,
                }
            )

        q_open = self.db.query(ComplianceAssessment).filter(
            ComplianceAssessment.status.in_(["pending", "in_progress"])
        )
        q_done = self.db.query(ComplianceAssessment).filter(
            ComplianceAssessment.status == "completed",
            ComplianceAssessment.finished_at
            >= _utcnow() - timedelta(days=30),
        )
        if tenant_id:
            q_open = q_open.filter(ComplianceAssessment.tenant_id == tenant_id)
            q_done = q_done.filter(ComplianceAssessment.tenant_id == tenant_id)

        scores = self.list_scores(tenant_id=tenant_id)
        evidence_q = self.db.query(ComplianceEvidence).filter(
            ComplianceEvidence.status == "valid"
        )
        if tenant_id:
            evidence_q = evidence_q.filter(ComplianceEvidence.tenant_id == tenant_id)

        scored = [s.score for s in scores]
        avg = round(sum(scored) / len(scored), 1) if scored else None
        below = sum(1 for s in scores if s.score < 70)

        return ComplianceFleetSummary(
            frameworks_enabled=len(frameworks),
            controls_total=controls_total,
            assessments_open=q_open.count(),
            assessments_completed_30d=q_done.count(),
            evidence_count=evidence_q.count(),
            avg_score=avg,
            frameworks_below_threshold=below,
            by_framework=by_fw,
        )
