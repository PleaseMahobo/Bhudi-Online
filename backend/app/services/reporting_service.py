from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.reporting import (
    REPORT_FORMATS,
    SYSTEM_TEMPLATES,
    ReportDefinition,
    ReportRun,
    ReportSchedule,
    ReportTemplate,
)
from app.schemas.reporting import (
    AssetReportSummary,
    ExecutiveDashboard,
    PatchComplianceSummary,
    ReportDefinitionCreate,
    ReportDefinitionUpdate,
    ReportRunCreate,
    ReportScheduleCreate,
    ReportScheduleUpdate,
    ReportTemplateCreate,
    ReportTemplateUpdate,
    SecurityComplianceSummary,
)
from app.services.email_service import EmailService, normalize_recipients


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _next_run(frequency: str, from_dt: datetime | None = None) -> datetime:
    base = from_dt or _utcnow()
    if frequency == "hourly":
        return base + timedelta(hours=1)
    if frequency == "daily":
        return base + timedelta(days=1)
    if frequency == "weekly":
        return base + timedelta(weeks=1)
    if frequency == "monthly":
        return base + timedelta(days=30)
    if frequency == "quarterly":
        return base + timedelta(days=90)
    return base + timedelta(days=7)


CONTENT_TYPES = {
    "csv": "text/csv",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "json": "application/json",
}

_EXPORT_CACHE: dict[str, bytes] = {}


class ReportingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "template_key": t["template_key"],
                "name": t["name"],
                "description": t.get("description"),
                "report_type": t["report_type"],
                "audience": t["audience"],
                "default_format": t["default_format"],
            }
            for t in SYSTEM_TEMPLATES
        ]

    def seed_templates(self, tenant_id: UUID | None = None) -> list[ReportTemplate]:
        created: list[ReportTemplate] = []
        for item in SYSTEM_TEMPLATES:
            existing = (
                self.db.query(ReportTemplate)
                .filter(
                    ReportTemplate.template_key == item["template_key"],
                    ReportTemplate.tenant_id == tenant_id,
                )
                .first()
            )
            if existing:
                created.append(existing)
                continue
            row = ReportTemplate(
                tenant_id=tenant_id,
                template_key=item["template_key"],
                name=item["name"],
                description=item.get("description"),
                report_type=item["report_type"],
                audience=item["audience"],
                default_format=item["default_format"],
                definition=item.get("definition"),
                is_system=True,
                enabled=True,
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for r in created:
            self.db.refresh(r)
        return created

    def create_template(self, payload: ReportTemplateCreate) -> ReportTemplate:
        row = ReportTemplate(
            tenant_id=payload.tenant_id,
            template_key=payload.template_key,
            name=payload.name,
            description=payload.description,
            report_type=payload.report_type,
            audience=payload.audience,
            default_format=payload.default_format,
            definition=payload.definition,
            is_system=False,
            enabled=payload.enabled,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_templates(
        self, *, enabled_only: bool = False, report_type: str | None = None, tenant_id: UUID | None = None,
    ) -> list[ReportTemplate]:
        q = self.db.query(ReportTemplate)
        if tenant_id is not None:
            q = q.filter((ReportTemplate.tenant_id == tenant_id) | (ReportTemplate.tenant_id.is_(None)))
        if enabled_only:
            q = q.filter(ReportTemplate.enabled.is_(True))
        if report_type:
            q = q.filter(ReportTemplate.report_type == report_type)
        return q.order_by(ReportTemplate.name).all()

    def get_template(self, template_id: UUID) -> ReportTemplate | None:
        return self.db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()

    def update_template(self, template_id: UUID, payload: ReportTemplateUpdate) -> ReportTemplate | None:
        row = self.get_template(template_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_template(self, template_id: UUID) -> bool:
        row = self.get_template(template_id)
        if not row:
            return False
        if row.is_system and row.tenant_id is None:
            row.enabled = False
            self.db.commit()
            return True
        self.db.delete(row)
        self.db.commit()
        return True

    def create_definition(self, payload: ReportDefinitionCreate) -> ReportDefinition:
        row = ReportDefinition(
            tenant_id=payload.tenant_id, name=payload.name, description=payload.description,
            report_type=payload.report_type, audience=payload.audience,
            config=payload.config or {}, created_by=payload.created_by,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_definitions(self, *, tenant_id: UUID | None = None, report_type: str | None = None) -> list[ReportDefinition]:
        q = self.db.query(ReportDefinition)
        if tenant_id is not None:
            q = q.filter(ReportDefinition.tenant_id == tenant_id)
        if report_type:
            q = q.filter(ReportDefinition.report_type == report_type)
        return q.order_by(ReportDefinition.updated_at.desc()).all()

    def get_definition(self, definition_id: UUID) -> ReportDefinition | None:
        return self.db.query(ReportDefinition).filter(ReportDefinition.id == definition_id).first()

    def update_definition(self, definition_id: UUID, payload: ReportDefinitionUpdate) -> ReportDefinition | None:
        row = self.get_definition(definition_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_definition(self, definition_id: UUID) -> bool:
        row = self.get_definition(definition_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def executive_dashboard(self, tenant_id: UUID | None = None) -> ExecutiveDashboard:
        devices_total = devices_online = devices_offline = 0
        open_alerts = critical_alerts = open_tickets = incidents_open = 0
        avg_security = avg_compliance = patch_pct = None
        backup_failed = 0
        by_section: dict[str, Any] = {}
        try:
            from app.models.device import Device
            q = self.db.query(Device)
            if tenant_id and hasattr(Device, "tenant_id"):
                q = q.filter(Device.tenant_id == tenant_id)
            devices_total = q.count()
            if hasattr(Device, "status"):
                devices_online = q.filter(Device.status == "online").count()
                devices_offline = q.filter(Device.status == "offline").count()
        except Exception:
            pass
        try:
            from app.models.alert import Alert
            aq = self.db.query(Alert)
            if tenant_id and hasattr(Alert, "tenant_id"):
                aq = aq.filter(Alert.tenant_id == tenant_id)
            if hasattr(Alert, "status"):
                open_alerts = aq.filter(Alert.status.in_(["open", "active", "firing"])).count()
            if hasattr(Alert, "severity"):
                critical_alerts = aq.filter(Alert.severity.in_(["critical", "high"])).count()
        except Exception:
            pass
        try:
            from app.models.itsm import ServiceTicket
            tq = self.db.query(ServiceTicket)
            if tenant_id and hasattr(ServiceTicket, "tenant_id"):
                tq = tq.filter(ServiceTicket.tenant_id == tenant_id)
            if hasattr(ServiceTicket, "status"):
                open_tickets = tq.filter(ServiceTicket.status.in_(["open", "in_progress", "pending"])).count()
        except Exception:
            pass
        try:
            from app.models.incident import Incident
            iq = self.db.query(Incident)
            if tenant_id and hasattr(Incident, "tenant_id"):
                iq = iq.filter(Incident.tenant_id == tenant_id)
            if hasattr(Incident, "status"):
                incidents_open = iq.filter(Incident.status.in_(["open", "investigating", "active"])).count()
        except Exception:
            pass
        try:
            from app.models.endpoint_security import EndpointSecurityScore
            sq = self.db.query(EndpointSecurityScore)
            if tenant_id and hasattr(EndpointSecurityScore, "tenant_id"):
                sq = sq.filter(EndpointSecurityScore.tenant_id == tenant_id)
            scores = [s.score for s in sq.all() if getattr(s, "score", None) is not None]
            if scores:
                avg_security = round(sum(scores) / len(scores), 1)
        except Exception:
            pass
        try:
            from app.models.compliance import ComplianceScore
            cq = self.db.query(ComplianceScore)
            if tenant_id and hasattr(ComplianceScore, "tenant_id"):
                cq = cq.filter(ComplianceScore.tenant_id == tenant_id)
            cscores = [s.score for s in cq.all() if getattr(s, "score", None) is not None]
            if cscores:
                avg_compliance = round(sum(cscores) / len(cscores), 1)
        except Exception:
            pass
        try:
            from app.models.backup_integration import BackupJob
            since = _utcnow() - timedelta(hours=24)
            bq = self.db.query(BackupJob)
            if hasattr(BackupJob, "status") and hasattr(BackupJob, "created_at"):
                backup_failed = bq.filter(BackupJob.status.in_(["failed", "error"]), BackupJob.created_at >= since).count()
        except Exception:
            pass
        if devices_total > 0:
            patch_pct = round((devices_online / devices_total) * 100, 1)
        by_section = {
            "fleet": {"total": devices_total, "online": devices_online, "offline": devices_offline},
            "alerts": {"open": open_alerts, "critical": critical_alerts},
            "tickets": {"open": open_tickets},
            "incidents": {"open": incidents_open},
            "security": {"avg_score": avg_security},
            "compliance": {"avg_score": avg_compliance},
            "backup": {"failed_24h": backup_failed},
        }
        return ExecutiveDashboard(
            devices_total=devices_total, devices_online=devices_online, devices_offline=devices_offline,
            open_alerts=open_alerts, critical_alerts=critical_alerts, open_tickets=open_tickets,
            avg_security_score=avg_security, avg_compliance_score=avg_compliance,
            patch_compliance_pct=patch_pct, backup_jobs_failed_24h=backup_failed,
            incidents_open=incidents_open, generated_at=_utcnow(), by_section=by_section,
        )

    def patch_compliance_summary(self, tenant_id: UUID | None = None) -> PatchComplianceSummary:
        devices_total = online = 0
        by_os: list[dict[str, Any]] = []
        try:
            from app.models.device import Device
            from sqlalchemy import func
            q = self.db.query(Device)
            if tenant_id and hasattr(Device, "tenant_id"):
                q = q.filter(Device.tenant_id == tenant_id)
            devices_total = q.count()
            if hasattr(Device, "status"):
                online = q.filter(Device.status == "online").count()
            if hasattr(Device, "os_name"):
                rows = q.with_entities(Device.os_name, func.count(Device.id)).group_by(Device.os_name).all()
                by_os = [{"os": r[0] or "unknown", "count": r[1]} for r in rows]
            elif hasattr(Device, "platform"):
                rows = q.with_entities(Device.platform, func.count(Device.id)).group_by(Device.platform).all()
                by_os = [{"os": r[0] or "unknown", "count": r[1]} for r in rows]
        except Exception:
            pass
        noncompliant = max(devices_total - online, 0)
        pct = round((online / devices_total) * 100, 1) if devices_total else None
        return PatchComplianceSummary(
            devices_total=devices_total, devices_compliant=online, devices_noncompliant=noncompliant,
            compliance_pct=pct, critical_missing=noncompliant, by_os=by_os, generated_at=_utcnow(),
        )

    def security_compliance_summary(self, tenant_id: UUID | None = None) -> SecurityComplianceSummary:
        avg_endpoint = None
        open_findings = critical_findings = frameworks_scored = 0
        avg_fw = None
        by_fw: list[dict[str, Any]] = []
        try:
            from app.models.endpoint_security import EndpointSecurityScore, SecurityFinding
            sq = self.db.query(EndpointSecurityScore)
            if tenant_id and hasattr(EndpointSecurityScore, "tenant_id"):
                sq = sq.filter(EndpointSecurityScore.tenant_id == tenant_id)
            scores = [s.score for s in sq.all() if getattr(s, "score", None) is not None]
            if scores:
                avg_endpoint = round(sum(scores) / len(scores), 1)
            fq = self.db.query(SecurityFinding)
            if tenant_id and hasattr(SecurityFinding, "tenant_id"):
                fq = fq.filter(SecurityFinding.tenant_id == tenant_id)
            if hasattr(SecurityFinding, "status"):
                open_findings = fq.filter(SecurityFinding.status.in_(["open", "active", "new"])).count()
            if hasattr(SecurityFinding, "severity"):
                critical_findings = fq.filter(SecurityFinding.severity.in_(["critical", "high"])).count()
        except Exception:
            pass
        try:
            from app.models.compliance import ComplianceScore
            cq = self.db.query(ComplianceScore).options(joinedload(ComplianceScore.framework))
            if tenant_id:
                cq = cq.filter(ComplianceScore.tenant_id == tenant_id)
            rows = cq.all()
            frameworks_scored = len(rows)
            if rows:
                avg_fw = round(sum(r.score for r in rows) / len(rows), 1)
                by_fw = [{
                    "framework_key": getattr(r.framework, "framework_key", None),
                    "display_name": getattr(r.framework, "display_name", None),
                    "score": r.score, "grade": r.grade,
                } for r in rows]
        except Exception:
            pass
        return SecurityComplianceSummary(
            avg_endpoint_score=avg_endpoint, open_findings=open_findings,
            critical_findings=critical_findings, frameworks_scored=frameworks_scored,
            avg_framework_score=avg_fw, generated_at=_utcnow(), by_framework=by_fw,
        )

    def asset_summary(self, tenant_id: UUID | None = None) -> AssetReportSummary:
        assets_total = licenses_expiring = warranty_expiring = 0
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        try:
            from app.models.asset_management import Asset
            from sqlalchemy import func
            q = self.db.query(Asset)
            if tenant_id and hasattr(Asset, "tenant_id"):
                q = q.filter(Asset.tenant_id == tenant_id)
            assets_total = q.count()
            if hasattr(Asset, "status"):
                rows = q.with_entities(Asset.status, func.count(Asset.id)).group_by(Asset.status).all()
                by_status = {str(r[0] or "unknown"): r[1] for r in rows}
            if hasattr(Asset, "asset_type"):
                rows = q.with_entities(Asset.asset_type, func.count(Asset.id)).group_by(Asset.asset_type).all()
                by_type = {str(r[0] or "unknown"): r[1] for r in rows}
        except Exception:
            pass
        try:
            from app.models.asset_management import License
            now = _utcnow()
            soon = now + timedelta(days=30)
            lq = self.db.query(License)
            if tenant_id and hasattr(License, "tenant_id"):
                lq = lq.filter(License.tenant_id == tenant_id)
            if hasattr(License, "expires_at"):
                licenses_expiring = lq.filter(License.expires_at >= now, License.expires_at <= soon).count()
        except Exception:
            pass
        return AssetReportSummary(
            assets_total=assets_total, by_status=by_status, by_type=by_type,
            licenses_expiring_30d=licenses_expiring, warranty_expiring_90d=warranty_expiring,
            generated_at=_utcnow(),
        )

    def _build_report_data(self, report_type: str, tenant_id: UUID | None, parameters: dict[str, Any] | None) -> dict[str, Any]:
        params = parameters or {}
        if report_type == "executive":
            return self.executive_dashboard(tenant_id).model_dump(mode="json")
        if report_type == "patch_compliance":
            return self.patch_compliance_summary(tenant_id).model_dump(mode="json")
        if report_type == "security_compliance":
            return self.security_compliance_summary(tenant_id).model_dump(mode="json")
        if report_type == "asset":
            return self.asset_summary(tenant_id).model_dump(mode="json")
        if report_type == "customer":
            dash = self.executive_dashboard(tenant_id)
            return {"title": "Customer SLA Report", "period": params.get("period", "last_30_days"),
                    "uptime_pct": dash.patch_compliance_pct, "open_tickets": dash.open_tickets,
                    "devices_total": dash.devices_total, "devices_online": dash.devices_online,
                    "generated_at": dash.generated_at.isoformat()}
        if report_type == "technician":
            dash = self.executive_dashboard(tenant_id)
            return {"title": "Technician Workload", "open_tickets": dash.open_tickets,
                    "critical_alerts": dash.critical_alerts, "offline_devices": dash.devices_offline,
                    "open_incidents": dash.incidents_open, "generated_at": dash.generated_at.isoformat()}
        return {"report_type": report_type, "parameters": params, "generated_at": _utcnow().isoformat(), "note": "Custom report payload"}

    def _flatten_rows(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key in ("by_framework", "by_os"):
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict):
                        rows.append(item)
                if rows:
                    return rows
        if "by_section" in data and isinstance(data["by_section"], dict):
            for section, vals in data["by_section"].items():
                if isinstance(vals, dict):
                    row = {"section": section}
                    row.update(vals)
                    rows.append(row)
                else:
                    rows.append({"section": section, "value": vals})
            if rows:
                return rows
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                continue
            rows.append({"metric": k, "value": v})
        return rows or [{"status": "empty"}]

    def _export_csv(self, data: dict[str, Any]) -> tuple[bytes, str, int]:
        rows = self._flatten_rows(data)
        buf = io.StringIO()
        if not rows:
            buf.write("metric,value\nempty,\n")
            return buf.getvalue().encode("utf-8"), CONTENT_TYPES["csv"], 0
        fieldnames = list(rows[0].keys())
        for r in rows[1:]:
            for k in r:
                if k not in fieldnames:
                    fieldnames.append(k)
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        content = buf.getvalue().encode("utf-8")
        return content, CONTENT_TYPES["csv"], len(rows)

    def _export_json(self, data: dict[str, Any]) -> tuple[bytes, str, int]:
        content = json.dumps(data, default=str, indent=2).encode("utf-8")
        return content, CONTENT_TYPES["json"], len(self._flatten_rows(data))

    def _export_excel(self, data: dict[str, Any]) -> tuple[bytes, str, int]:
        rows = self._flatten_rows(data) or [{"metric": "empty", "value": ""}]
        fieldnames = list(rows[0].keys())
        for r in rows[1:]:
            for k in r:
                if k not in fieldnames:
                    fieldnames.append(k)

        def _esc(v: Any) -> str:
            s = "" if v is None else str(v)
            return s.replace("&", "&").replace("<", "<").replace(">", ">").replace('"', """)

        parts = [
            '<?xml version="1.0"?>', '<?mso-application progid="Excel.Sheet"?>',
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
            ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
            '<Worksheet ss:Name="Report"><Table>',
        ]
        parts.append("<Row>")
        for h in fieldnames:
            parts.append(f'<Cell><Data ss:Type="String">{_esc(h)}</Data></Cell>')
        parts.append("</Row>")
        for r in rows:
            parts.append("<Row>")
            for h in fieldnames:
                val = r.get(h, "")
                typ = "Number" if isinstance(val, (int, float)) and not isinstance(val, bool) else "String"
                parts.append(f'<Cell><Data ss:Type="{typ}">{_esc(val)}</Data></Cell>')
            parts.append("</Row>")
        parts.append("</Table></Worksheet></Workbook>")
        return "\n".join(parts).encode("utf-8"), "application/vnd.ms-excel", len(rows)

    def _export_pdf(self, data: dict[str, Any], title: str) -> tuple[bytes, str, int]:
        lines = [title, "=" * len(title), ""]
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{k}:")
                lines.append(json.dumps(v, default=str, indent=2)[:2000])
            else:
                lines.append(f"{k}: {v}")
        text = "\n".join(lines)
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_stream = f"BT /F1 10 Tf 50 750 Td 12 TL ({safe[:4000]}) Tj ET"
        objects: list[bytes | str] = []
        objects.append("1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
        objects.append("2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
        objects.append("3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n")
        stream = content_stream.encode("latin-1", errors="replace")
        objects.append(f"4 0 obj<< /Length {len(stream)} >>stream\n".encode() + stream + b"\nendstream\nendobj\n")
        objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
        out = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(out))
            out.extend(obj.encode("latin-1", errors="replace") if isinstance(obj, str) else obj)
        xref_pos = len(out)
        out.extend(f"xref\n0 {len(offsets)}\n".encode())
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode())
        out.extend(f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
        return bytes(out), CONTENT_TYPES["pdf"], len(self._flatten_rows(data))

    def _render_export(self, fmt: str, data: dict[str, Any], title: str) -> tuple[bytes, str, int]:
        fmt = (fmt or "json").lower()
        if fmt not in REPORT_FORMATS:
            fmt = "json"
        if fmt == "csv":
            return self._export_csv(data)
        if fmt == "excel":
            return self._export_excel(data)
        if fmt == "pdf":
            return self._export_pdf(data, title)
        return self._export_json(data)

    def create_run(self, payload: ReportRunCreate) -> ReportRun:
        report_type = payload.report_type or "custom"
        name = payload.name
        audience = payload.audience
        if payload.template_id:
            template = self.get_template(payload.template_id)
            if not template:
                raise ValueError("Template not found")
            report_type = template.report_type
            audience = template.audience
            name = name or template.name
        if payload.definition_id:
            definition = self.get_definition(payload.definition_id)
            if not definition:
                raise ValueError("Definition not found")
            report_type = definition.report_type
            audience = definition.audience
            name = name or definition.name
        name = name or f"{report_type} report"
        row = ReportRun(
            tenant_id=payload.tenant_id, template_id=payload.template_id, definition_id=payload.definition_id,
            name=name, report_type=report_type, audience=audience, format=payload.format,
            status="pending", parameters=payload.parameters, triggered_by=payload.triggered_by,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        if payload.run_now:
            row = self.execute_run(row.id)
        return row

    def execute_run(self, run_id: UUID) -> ReportRun:
        row = self.get_run(run_id)
        if not row:
            raise ValueError("Run not found")
        row.status = "running"
        row.started_at = _utcnow()
        row.error_message = None
        self.db.commit()
        try:
            data = self._build_report_data(row.report_type, row.tenant_id, row.parameters)
            content, content_type, row_count = self._render_export(row.format, data, row.name)
            row.result_data = {**data, "_export_meta": {"content_type": content_type, "size_bytes": len(content), "format": row.format}}
            row.storage_uri = f"memory://reports/{row.id}.{row.format}"
            row.content_type = content_type
            row.size_bytes = len(content)
            row.row_count = row_count
            row.status = "completed"
            row.finished_at = _utcnow()
            row.expires_at = _utcnow() + timedelta(days=30)
            self.db.commit()
            self.db.refresh(row)
            _EXPORT_CACHE[str(row.id)] = content
            return row
        except Exception as exc:
            row.status = "failed"
            row.error_message = str(exc)[:2000]
            row.finished_at = _utcnow()
            self.db.commit()
            self.db.refresh(row)
            return row

    def get_run_bytes(self, run_id: UUID) -> tuple[bytes, str, str] | None:
        row = self.get_run(run_id)
        if not row or row.status != "completed":
            return None
        cached = _EXPORT_CACHE.get(str(run_id))
        if cached is None:
            data = row.result_data or self._build_report_data(row.report_type, row.tenant_id, row.parameters)
            clean = {k: v for k, v in data.items() if not str(k).startswith("_")}
            cached, content_type, _ = self._render_export(row.format, clean, row.name)
            _EXPORT_CACHE[str(run_id)] = cached
        else:
            content_type = row.content_type or CONTENT_TYPES.get(row.format, "application/octet-stream")
        ext = {"excel": "xls", "pdf": "pdf", "csv": "csv", "json": "json"}.get(row.format, "bin")
        return cached, content_type, f"{row.report_type}_{row.id}.{ext}"

    def list_runs(self, *, tenant_id: UUID | None = None, report_type: str | None = None, status: str | None = None, limit: int = 50) -> list[ReportRun]:
        q = self.db.query(ReportRun)
        if tenant_id is not None:
            q = q.filter(ReportRun.tenant_id == tenant_id)
        if report_type:
            q = q.filter(ReportRun.report_type == report_type)
        if status:
            q = q.filter(ReportRun.status == status)
        return q.order_by(ReportRun.created_at.desc()).limit(limit).all()

    def get_run(self, run_id: UUID) -> ReportRun | None:
        return self.db.query(ReportRun).filter(ReportRun.id == run_id).first()

    def delete_run(self, run_id: UUID) -> bool:
        row = self.get_run(run_id)
        if not row:
            return False
        _EXPORT_CACHE.pop(str(run_id), None)
        self.db.delete(row)
        self.db.commit()
        return True

    def create_schedule(self, payload: ReportScheduleCreate) -> ReportSchedule:
        if not payload.template_id and not payload.definition_id:
            raise ValueError("template_id or definition_id required")
        row = ReportSchedule(
            tenant_id=payload.tenant_id, template_id=payload.template_id, definition_id=payload.definition_id,
            name=payload.name, frequency=payload.frequency, cron_hint=payload.cron_hint,
            format=payload.format, parameters=payload.parameters, recipients=payload.recipients,
            enabled=payload.enabled, created_by=payload.created_by, next_run_at=_next_run(payload.frequency),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_schedules(self, *, tenant_id: UUID | None = None, enabled_only: bool = False) -> list[ReportSchedule]:
        q = self.db.query(ReportSchedule)
        if tenant_id is not None:
            q = q.filter(ReportSchedule.tenant_id == tenant_id)
        if enabled_only:
            q = q.filter(ReportSchedule.enabled.is_(True))
        return q.order_by(ReportSchedule.next_run_at.asc().nullslast()).all()

    def get_schedule(self, schedule_id: UUID) -> ReportSchedule | None:
        return self.db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()

    def update_schedule(self, schedule_id: UUID, payload: ReportScheduleUpdate) -> ReportSchedule | None:
        row = self.get_schedule(schedule_id)
        if not row:
            return None
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(row, k, v)
        if "frequency" in data:
            row.next_run_at = _next_run(row.frequency)
        row.updated_at = _utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_schedule(self, schedule_id: UUID) -> bool:
        row = self.get_schedule(schedule_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def _summary_lines(self, data: dict[str, Any] | None) -> list[str]:
        if not data:
            return []
        lines: list[str] = []
        skip = {"_export_meta", "_email_delivery"}
        for k, v in data.items():
            if k in skip or isinstance(v, (dict, list)):
                continue
            lines.append(f"{k}: {v}")
        if "by_section" in data and isinstance(data["by_section"], dict):
            for section, vals in data["by_section"].items():
                if isinstance(vals, dict):
                    parts = ", ".join(f"{a}={b}" for a, b in vals.items())
                    lines.append(f"{section}: {parts}")
                else:
                    lines.append(f"{section}: {vals}")
        return lines[:20]

    def deliver_run_email(
        self, run_id: UUID, *, recipients: list[str] | None = None, schedule_name: str | None = None,
    ) -> dict[str, Any]:
        """Email a completed report run to recipients (attachment included)."""
        row = self.get_run(run_id)
        if not row:
            raise ValueError("Run not found")
        if row.status != "completed":
            raise ValueError(f"Run status is {row.status}, expected completed")
        to = normalize_recipients(recipients)
        if not to and row.schedule_id:
            sched = self.get_schedule(row.schedule_id)
            if sched:
                to = normalize_recipients(sched.recipients)
                schedule_name = schedule_name or sched.name
        if not to:
            raise ValueError("No recipients provided")
        blob = self.get_run_bytes(run_id)
        if not blob:
            raise ValueError("Report bytes unavailable")
        content, content_type, filename = blob
        data = row.result_data or {}
        clean = {k: v for k, v in data.items() if not str(k).startswith("_")}
        result = EmailService().send_report(
            recipients=to, report_name=row.name, report_type=row.report_type, format=row.format,
            attachment_bytes=content, filename=filename, content_type=content_type,
            summary_lines=self._summary_lines(clean), schedule_name=schedule_name,
        )
        delivery = {
            "ok": result.ok, "skipped": result.skipped, "recipients": result.recipients,
            "message_id": result.message_id, "error": result.error, "sent_at": _utcnow().isoformat(),
        }
        meta = dict(row.result_data or {})
        meta["_email_delivery"] = delivery
        row.result_data = meta
        self.db.commit()
        self.db.refresh(row)
        return delivery

    def process_due_schedules(self, limit: int = 20) -> list[ReportRun]:
        """Execute due schedules, then email recipients when configured."""
        now = _utcnow()
        due = (
            self.db.query(ReportSchedule)
            .filter(ReportSchedule.enabled.is_(True), ReportSchedule.next_run_at <= now)
            .limit(limit).all()
        )
        runs: list[ReportRun] = []
        for sched in due:
            try:
                run = self.create_run(ReportRunCreate(
                    name=sched.name, template_id=sched.template_id, definition_id=sched.definition_id,
                    format=sched.format, parameters=sched.parameters, tenant_id=sched.tenant_id,
                    triggered_by=f"schedule:{sched.id}", run_now=True,
                ))
                run.schedule_id = sched.id
                self.db.commit()
                if run.status == "completed" and sched.recipients:
                    try:
                        self.deliver_run_email(
                            run.id, recipients=list(sched.recipients or []), schedule_name=sched.name,
                        )
                        self.db.refresh(run)
                    except Exception as mail_exc:
                        meta = dict(run.result_data or {})
                        meta["_email_delivery"] = {
                            "ok": False, "error": str(mail_exc)[:1000], "sent_at": _utcnow().isoformat(),
                        }
                        run.result_data = meta
                        self.db.commit()
                sched.last_run_at = now
                sched.last_run_status = run.status
                sched.run_count = (sched.run_count or 0) + 1
                sched.next_run_at = _next_run(sched.frequency, now)
                self.db.commit()
                runs.append(run)
            except Exception:
                sched.last_run_at = now
                sched.last_run_status = "failed"
                sched.next_run_at = _next_run(sched.frequency, now)
                self.db.commit()
        return runs
