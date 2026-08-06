from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.endpoint_security import (
    SECURITY_PROVIDERS,
    EndpointSecurityAgent,
    EndpointSecurityScore,
    SecurityFinding,
    SecurityProvider,
)
from app.schemas.endpoint_security import (
    AgentIngestPayload,
    EndpointSecurityAgentCreate,
    EndpointSecurityAgentUpdate,
    FindingIngestPayload,
    OrgSecurityScoreResponse,
    SecurityFindingCreate,
    SecurityFindingUpdate,
    SecurityProviderCreate,
    SecurityProviderUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


# Default catalog for seed / list-available
PROVIDER_CATALOG: list[dict[str, str]] = [
    {"provider_key": "windows_defender", "display_name": "Windows Defender"},
    {"provider_key": "microsoft_defender_xdr", "display_name": "Microsoft Defender XDR"},
    {"provider_key": "threatlocker", "display_name": "ThreatLocker"},
    {"provider_key": "huntress", "display_name": "Huntress"},
    {"provider_key": "sentinelone", "display_name": "SentinelOne"},
    {"provider_key": "crowdstrike", "display_name": "CrowdStrike"},
    {"provider_key": "bitdefender", "display_name": "Bitdefender"},
    {"provider_key": "sophos", "display_name": "Sophos"},
    {"provider_key": "malwarebytes", "display_name": "Malwarebytes"},
]


class EndpointSecurityService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- Providers ----------

    def list_catalog(self) -> list[dict[str, str]]:
        return list(PROVIDER_CATALOG)

    def create_provider(self, payload: SecurityProviderCreate) -> SecurityProvider:
        key = payload.provider_key.strip().lower()
        if key not in SECURITY_PROVIDERS and key not in {
            p["provider_key"] for p in PROVIDER_CATALOG
        }:
            # Allow extension keys but prefer catalog
            pass
        row = SecurityProvider(
            provider_key=key,
            display_name=payload.display_name,
            enabled=payload.enabled,
            config=payload.config,
            notes=payload.notes,
            tenant_id=payload.tenant_id,
            last_sync_status="never",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_providers(
        self, *, enabled_only: bool = False, tenant_id: UUID | None = None
    ) -> list[SecurityProvider]:
        q = self.db.query(SecurityProvider)
        if enabled_only:
            q = q.filter(SecurityProvider.enabled.is_(True))
        if tenant_id:
            q = q.filter(SecurityProvider.tenant_id == tenant_id)
        return q.order_by(SecurityProvider.display_name.asc()).all()

    def get_provider(self, provider_id: UUID) -> SecurityProvider | None:
        return self.db.get(SecurityProvider, provider_id)

    def get_provider_by_key(
        self, provider_key: str, tenant_id: UUID | None = None
    ) -> SecurityProvider | None:
        q = self.db.query(SecurityProvider).filter(
            SecurityProvider.provider_key == provider_key.strip().lower()
        )
        if tenant_id:
            q = q.filter(SecurityProvider.tenant_id == tenant_id)
        return q.first()

    def update_provider(
        self, provider_id: UUID, payload: SecurityProviderUpdate
    ) -> SecurityProvider | None:
        row = self.get_provider(provider_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_provider(self, provider_id: UUID) -> bool:
        row = self.get_provider(provider_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def seed_default_providers(self, tenant_id: UUID | None = None) -> list[SecurityProvider]:
        """Idempotently ensure catalog providers exist (disabled by default)."""
        created: list[SecurityProvider] = []
        for item in PROVIDER_CATALOG:
            existing = self.get_provider_by_key(item["provider_key"], tenant_id=tenant_id)
            if existing:
                continue
            row = SecurityProvider(
                provider_key=item["provider_key"],
                display_name=item["display_name"],
                enabled=False,
                tenant_id=tenant_id,
                last_sync_status="never",
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for r in created:
            self.db.refresh(r)
        return created

    # ---------- Agents ----------

    def create_agent(self, payload: EndpointSecurityAgentCreate) -> EndpointSecurityAgent:
        if not self.get_provider(payload.provider_id):
            raise ValueError("Provider not found")
        row = EndpointSecurityAgent(**payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        if row.device_id:
            self.compute_device_score(row.device_id)
        return row

    def list_agents(
        self,
        *,
        device_id: UUID | None = None,
        provider_id: UUID | None = None,
        status: str | None = None,
    ) -> list[EndpointSecurityAgent]:
        q = self.db.query(EndpointSecurityAgent).options(
            joinedload(EndpointSecurityAgent.provider)
        )
        if device_id:
            q = q.filter(EndpointSecurityAgent.device_id == device_id)
        if provider_id:
            q = q.filter(EndpointSecurityAgent.provider_id == provider_id)
        if status:
            q = q.filter(EndpointSecurityAgent.status == status)
        return q.order_by(EndpointSecurityAgent.updated_at.desc()).all()

    def update_agent(
        self, agent_id: UUID, payload: EndpointSecurityAgentUpdate
    ) -> EndpointSecurityAgent | None:
        row = self.db.get(EndpointSecurityAgent, agent_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        if row.device_id:
            self.compute_device_score(row.device_id)
        return row

    def delete_agent(self, agent_id: UUID) -> bool:
        row = self.db.get(EndpointSecurityAgent, agent_id)
        if not row:
            return False
        device_id = row.device_id
        self.db.delete(row)
        self.db.commit()
        if device_id:
            self.compute_device_score(device_id)
        return True

    def ingest_agent(self, payload: AgentIngestPayload) -> EndpointSecurityAgent:
        provider = self.get_provider_by_key(payload.provider_key)
        if not provider:
            raise ValueError(f"Provider '{payload.provider_key}' is not configured")

        q = self.db.query(EndpointSecurityAgent).filter(
            EndpointSecurityAgent.provider_id == provider.id
        )
        if payload.device_id:
            q = q.filter(EndpointSecurityAgent.device_id == payload.device_id)
        elif payload.hostname:
            q = q.filter(EndpointSecurityAgent.hostname == payload.hostname)
        else:
            raise ValueError("device_id or hostname required")

        row = q.first()
        data = {
            "external_agent_id": payload.external_agent_id,
            "agent_version": payload.agent_version,
            "status": payload.status,
            "real_time_protection": payload.real_time_protection,
            "definitions_up_to_date": payload.definitions_up_to_date,
            "last_scan_at": payload.last_scan_at,
            "last_seen_at": payload.last_seen_at or _utcnow(),
            "details": payload.details,
            "hostname": payload.hostname,
            "device_id": payload.device_id,
        }
        if row:
            for k, v in data.items():
                if v is not None:
                    setattr(row, k, v)
        else:
            row = EndpointSecurityAgent(provider_id=provider.id, **data)
            self.db.add(row)

        provider.last_sync_at = _utcnow()
        provider.last_sync_status = "ok"
        self.db.commit()
        self.db.refresh(row)
        if row.device_id:
            self.compute_device_score(row.device_id)
        return row

    # ---------- Findings ----------

    def create_finding(self, payload: SecurityFindingCreate) -> SecurityFinding:
        if not self.get_provider(payload.provider_id):
            raise ValueError("Provider not found")
        row = SecurityFinding(**payload.model_dump())
        if not row.detected_at:
            row.detected_at = _utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        if row.device_id:
            self.compute_device_score(row.device_id)
        return row

    def list_findings(
        self,
        *,
        device_id: UUID | None = None,
        provider_id: UUID | None = None,
        status: str | None = None,
        severity: str | None = None,
    ) -> list[SecurityFinding]:
        q = self.db.query(SecurityFinding).options(
            joinedload(SecurityFinding.provider)
        )
        if device_id:
            q = q.filter(SecurityFinding.device_id == device_id)
        if provider_id:
            q = q.filter(SecurityFinding.provider_id == provider_id)
        if status:
            q = q.filter(SecurityFinding.status == status)
        if severity:
            q = q.filter(SecurityFinding.severity == severity)
        return q.order_by(SecurityFinding.detected_at.desc().nullslast()).all()

    def update_finding(
        self, finding_id: UUID, payload: SecurityFindingUpdate
    ) -> SecurityFinding | None:
        row = self.db.get(SecurityFinding, finding_id)
        if not row:
            return None
        data = payload.model_dump(exclude_unset=True)
        if data.get("status") in ("resolved", "false_positive") and not data.get(
            "resolved_at"
        ):
            data["resolved_at"] = _utcnow()
        for k, v in data.items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        if row.device_id:
            self.compute_device_score(row.device_id)
        return row

    def delete_finding(self, finding_id: UUID) -> bool:
        row = self.db.get(SecurityFinding, finding_id)
        if not row:
            return False
        device_id = row.device_id
        self.db.delete(row)
        self.db.commit()
        if device_id:
            self.compute_device_score(device_id)
        return True

    def ingest_finding(self, payload: FindingIngestPayload) -> SecurityFinding:
        provider = self.get_provider_by_key(payload.provider_key)
        if not provider:
            raise ValueError(f"Provider '{payload.provider_key}' is not configured")

        row = None
        if payload.external_id:
            row = (
                self.db.query(SecurityFinding)
                .filter(
                    SecurityFinding.provider_id == provider.id,
                    SecurityFinding.external_id == payload.external_id,
                )
                .first()
            )

        data = payload.model_dump(exclude={"provider_key"})
        if row:
            for k, v in data.items():
                if v is not None:
                    setattr(row, k, v)
        else:
            row = SecurityFinding(provider_id=provider.id, **data)
            if not row.detected_at:
                row.detected_at = _utcnow()
            self.db.add(row)

        provider.last_sync_at = _utcnow()
        provider.last_sync_status = "ok"
        self.db.commit()
        self.db.refresh(row)
        if row.device_id:
            self.compute_device_score(row.device_id)
        return row

    # ---------- Security score ----------

    def compute_device_score(self, device_id: UUID) -> EndpointSecurityScore:
        agents = (
            self.db.query(EndpointSecurityAgent)
            .filter(EndpointSecurityAgent.device_id == device_id)
            .all()
        )
        findings = (
            self.db.query(SecurityFinding)
            .filter(
                SecurityFinding.device_id == device_id,
                SecurityFinding.status.in_(["open", "investigating", "contained"]),
            )
            .all()
        )

        open_critical = sum(1 for f in findings if f.severity == "critical")
        open_high = sum(1 for f in findings if f.severity == "high")
        open_medium = sum(1 for f in findings if f.severity == "medium")

        agents_total = len(agents)
        agents_healthy = sum(1 for a in agents if a.status == "healthy")
        rtp_on = sum(1 for a in agents if a.real_time_protection is True)
        defs_ok = sum(1 for a in agents if a.definitions_up_to_date is True)

        # Start from 100 and subtract weighted penalties / add coverage credit
        score = 100
        factors: dict = {
            "agents_total": agents_total,
            "agents_healthy": agents_healthy,
            "rtp_on": rtp_on,
            "defs_ok": defs_ok,
            "open_critical": open_critical,
            "open_high": open_high,
            "open_medium": open_medium,
        }

        if agents_total == 0:
            score -= 40
            factors["no_agent"] = -40
        else:
            unhealthy = agents_total - agents_healthy
            pen = min(30, unhealthy * 15)
            score -= pen
            factors["unhealthy_agents"] = -pen

            if rtp_on < agents_total:
                pen = min(15, (agents_total - rtp_on) * 10)
                score -= pen
                factors["rtp_off"] = -pen

            if defs_ok < agents_total:
                pen = min(10, (agents_total - defs_ok) * 5)
                score -= pen
                factors["stale_definitions"] = -pen

        score -= open_critical * 25
        score -= open_high * 12
        score -= open_medium * 4
        factors["finding_penalty"] = -(
            open_critical * 25 + open_high * 12 + open_medium * 4
        )

        score = max(0, min(100, score))
        grade = _grade(score)

        hostname = None
        if agents:
            hostname = next((a.hostname for a in agents if a.hostname), None)

        row = (
            self.db.query(EndpointSecurityScore)
            .filter(EndpointSecurityScore.device_id == device_id)
            .first()
        )
        if not row:
            row = EndpointSecurityScore(device_id=device_id)
            self.db.add(row)

        row.hostname = hostname
        row.score = score
        row.grade = grade
        row.factors = factors
        row.open_critical = open_critical
        row.open_high = open_high
        row.agents_healthy = agents_healthy
        row.agents_total = agents_total
        row.computed_at = _utcnow()

        self.db.commit()
        self.db.refresh(row)
        return row

    def get_device_score(self, device_id: UUID) -> EndpointSecurityScore | None:
        return (
            self.db.query(EndpointSecurityScore)
            .filter(EndpointSecurityScore.device_id == device_id)
            .first()
        )

    def list_scores(self, *, min_score: int | None = None) -> list[EndpointSecurityScore]:
        q = self.db.query(EndpointSecurityScore)
        if min_score is not None:
            q = q.filter(EndpointSecurityScore.score >= min_score)
        return q.order_by(EndpointSecurityScore.score.asc()).all()

    def recompute_all_scores(self) -> int:
        device_ids = {
            a.device_id
            for a in self.db.query(EndpointSecurityAgent.device_id)
            .filter(EndpointSecurityAgent.device_id.isnot(None))
            .distinct()
        }
        for did in device_ids:
            self.compute_device_score(did)
        return len(device_ids)

    def org_score(self) -> OrgSecurityScoreResponse:
        scores = self.list_scores()
        values = [s.score for s in scores]
        grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for s in scores:
            grade_dist[s.grade] = grade_dist.get(s.grade, 0) + 1

        providers = self.list_providers(enabled_only=True)
        agents = self.list_agents()

        return OrgSecurityScoreResponse(
            devices_scored=len(scores),
            average_score=round(sum(values) / len(values), 2) if values else 0.0,
            median_score=float(median(values)) if values else 0.0,
            grade_distribution=grade_dist,
            open_critical_total=sum(s.open_critical for s in scores),
            open_high_total=sum(s.open_high for s in scores),
            providers_enabled=len(providers),
            agents_healthy=sum(1 for a in agents if a.status == "healthy"),
            agents_total=len(agents),
        )
