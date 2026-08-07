from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ai import AIRun, KnowledgeArticle, PredictionRecord
from app.schemas.ai import (
    AICapacityRequest,
    AIKnowledgeSearchRequest,
    AIPredictiveRequest,
    AIRemediationRequest,
    AIRootCauseRequest,
    AIScriptRequest,
    AITicketSummaryRequest,
    KnowledgeArticleCreate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AIService:
    """
    AI feature layer.

    When AI_ENABLED=true and AI_API_KEY + AI_BASE_URL are set, calls an
    OpenAI-compatible chat completions endpoint. Otherwise returns structured
    heuristic / template responses (dry-run) so the API is usable offline.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.enabled = os.getenv("AI_ENABLED", "false").lower() in ("1", "true", "yes", "on")
        self.api_key = os.getenv("AI_API_KEY", "")
        self.base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")

    def _record(
        self,
        task_type: str,
        *,
        tenant_id: UUID | None,
        input_data: dict[str, Any],
        output: dict[str, Any],
        status: str,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> AIRun:
        run = AIRun(
            tenant_id=tenant_id,
            task_type=task_type,
            model=self.model if status != "dry_run" else "heuristic",
            status=status,
            input_json=input_data,
            output_json=output,
            error=error,
            latency_ms=latency_ms,
            completed_at=_utcnow() if status in ("completed", "dry_run", "failed") else None,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _chat(self, system: str, user: str) -> dict[str, Any]:
        if not self.enabled or not self.api_key:
            return {"dry_run": True, "content": None}
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage") or {}
        return {
            "dry_run": False,
            "content": content,
            "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
        }

    # ---- features ----

    def root_cause(self, req: AIRootCauseRequest) -> AIRun:
        t0 = time.perf_counter()
        system = "You are an MSP root-cause analyst. Reply with JSON: likely_causes[], confidence, recommended_checks[], summary."
        user = f"Title: {req.title}\nSymptoms: {req.symptoms}\nContext: {json.dumps(req.context or {})}"
        try:
            chat = self._chat(system, user)
            if chat.get("dry_run") or not chat.get("content"):
                output = self._heuristic_rca(req)
                status = "dry_run"
            else:
                output = self._parse_json_block(chat["content"], fallback=self._heuristic_rca(req))
                status = "completed"
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("root_cause", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output=output, status=status, latency_ms=ms)
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("root_cause", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output={}, status="failed", latency_ms=ms, error=str(e))

    def generate_script(self, req: AIScriptRequest) -> AIRun:
        t0 = time.perf_counter()
        system = f"You generate safe {req.platform} scripts for MSP technicians. Return JSON: script, explanation, risks[]."
        user = f"Goal: {req.goal}\nConstraints: {req.constraints or 'none'}"
        try:
            chat = self._chat(system, user)
            if chat.get("dry_run") or not chat.get("content"):
                output = self._heuristic_script(req)
                status = "dry_run"
            else:
                output = self._parse_json_block(chat["content"], fallback=self._heuristic_script(req))
                status = "completed"
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("script_generation", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output=output, status=status, latency_ms=ms)
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("script_generation", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output={}, status="failed", latency_ms=ms, error=str(e))

    def remediation(self, req: AIRemediationRequest) -> AIRun:
        t0 = time.perf_counter()
        system = "You propose stepwise MSP remediation. Return JSON: steps[], rollback[], severity, summary."
        user = f"Issue: {req.issue}\nEnv: {json.dumps(req.environment or {})}"
        try:
            chat = self._chat(system, user)
            if chat.get("dry_run") or not chat.get("content"):
                output = {
                    "summary": f"Investigate and remediate: {req.issue}",
                    "severity": "medium",
                    "steps": [
                        "Capture current state / logs",
                        "Isolate affected scope if safety requires",
                        "Apply known fix or vendor guidance",
                        "Verify service restoration",
                        "Document outcome in ticket",
                    ],
                    "rollback": ["Revert last change if regression observed"],
                }
                status = "dry_run"
            else:
                output = self._parse_json_block(
                    chat["content"],
                    fallback={"summary": chat["content"], "steps": [], "rollback": []},
                )
                status = "completed"
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("remediation", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output=output, status=status, latency_ms=ms)
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("remediation", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output={}, status="failed", latency_ms=ms, error=str(e))

    def ticket_summary(self, req: AITicketSummaryRequest) -> AIRun:
        t0 = time.perf_counter()
        notes = "\n".join(req.work_notes or [])
        system = "Summarize ITSM tickets for technicians. Return JSON: summary, status_guess, next_actions[]."
        user = f"Title: {req.title}\nDescription: {req.description or ''}\nNotes:\n{notes}"
        try:
            chat = self._chat(system, user)
            if chat.get("dry_run") or not chat.get("content"):
                output = {
                    "summary": f"{req.title}: {(req.description or '')[:240]}",
                    "status_guess": "in_progress",
                    "next_actions": ["Confirm impact", "Update customer", "Schedule follow-up"],
                }
                status = "dry_run"
            else:
                output = self._parse_json_block(chat["content"], fallback={"summary": chat["content"]})
                status = "completed"
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("ticket_summary", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output=output, status=status, latency_ms=ms)
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            return self._record("ticket_summary", tenant_id=req.tenant_id, input_data=req.model_dump(mode="json"), output={}, status="failed", latency_ms=ms, error=str(e))

    def knowledge_search(self, req: AIKnowledgeSearchRequest) -> dict[str, Any]:
        q = self.db.query(KnowledgeArticle).filter(KnowledgeArticle.published.is_(True))
        if req.tenant_id is not None:
            q = q.filter(
                (KnowledgeArticle.tenant_id == req.tenant_id) | (KnowledgeArticle.tenant_id.is_(None))
            )
        rows = q.order_by(KnowledgeArticle.updated_at.desc()).limit(200).all()
        query_l = req.query.lower()
        scored = []
        for art in rows:
            blob = f"{art.title} {art.body}".lower()
            score = sum(1 for tok in query_l.split() if tok in blob)
            if score:
                scored.append((score, art))
        scored.sort(key=lambda x: x[0], reverse=True)
        hits = [
            {
                "id": str(a.id),
                "slug": a.slug,
                "title": a.title,
                "excerpt": a.body[:280],
                "score": s,
            }
            for s, a in scored[: req.limit]
        ]
        run = self._record(
            "knowledge",
            tenant_id=req.tenant_id,
            input_data=req.model_dump(mode="json"),
            output={"hits": hits},
            status="completed",
            latency_ms=0,
        )
        return {"run_id": str(run.id), "hits": hits}

    def predictive_failure(self, req: AIPredictiveRequest) -> AIRun:
        metrics = req.metrics or {}
        # Simple heuristic risk from disk/cpu/mem signals
        risk = 0.15
        reasons = []
        for key, weight in (("disk_pct", 0.4), ("cpu_pct", 0.25), ("mem_pct", 0.25), ("error_rate", 0.5)):
            val = metrics.get(key)
            if isinstance(val, (int, float)) and val >= 85:
                risk += weight * min(1.0, (val - 70) / 30)
                reasons.append(f"{key}={val}")
        risk = round(min(0.99, risk), 3)
        summary = (
            f"Elevated failure risk for {req.target_type}:{req.target_id} "
            f"over {req.horizon_hours}h"
            if risk >= 0.5
            else f"Low predicted failure risk for {req.target_type}:{req.target_id}"
        )
        details = {"reasons": reasons, "metrics": metrics, "score": risk}
        pred = PredictionRecord(
            tenant_id=req.tenant_id,
            kind="predictive_failure",
            target_type=req.target_type,
            target_id=req.target_id,
            score=risk,
            horizon_hours=req.horizon_hours,
            summary=summary,
            details=details,
        )
        self.db.add(pred)
        self.db.commit()
        return self._record(
            "predictive_failure",
            tenant_id=req.tenant_id,
            input_data=req.model_dump(mode="json"),
            output={"prediction_id": str(pred.id), "score": risk, "summary": summary, "details": details},
            status="dry_run",
            latency_ms=0,
        )

    def capacity_forecast(self, req: AICapacityRequest) -> AIRun:
        history = req.history or []
        values = [float(h["value"]) for h in history if isinstance(h.get("value"), (int, float))]
        if len(values) >= 2:
            # linear slope on last points
            slope = (values[-1] - values[0]) / max(1, len(values) - 1)
            projected = values[-1] + slope * max(1, req.horizon_hours // 24)
        elif values:
            slope = 0.0
            projected = values[-1]
        else:
            slope = 0.0
            projected = 0.0
        summary = (
            f"{req.resource} projected to {projected:.1f} in ~{req.horizon_hours}h "
            f"(slope {slope:.3f}/step)"
        )
        details = {"projected": projected, "slope": slope, "points": len(values)}
        pred = PredictionRecord(
            tenant_id=req.tenant_id,
            kind="capacity_forecast",
            target_type="resource",
            target_id=req.resource,
            score=projected,
            horizon_hours=req.horizon_hours,
            summary=summary,
            details=details,
        )
        self.db.add(pred)
        self.db.commit()
        return self._record(
            "capacity_forecast",
            tenant_id=req.tenant_id,
            input_data=req.model_dump(mode="json"),
            output={"prediction_id": str(pred.id), "summary": summary, "details": details},
            status="dry_run",
            latency_ms=0,
        )

    # ---- knowledge CRUD ----

    def create_article(self, payload: KnowledgeArticleCreate) -> KnowledgeArticle:
        row = KnowledgeArticle(
            slug=payload.slug.strip().lower(),
            title=payload.title,
            body=payload.body,
            tags=payload.tags,
            source=payload.source,
            published=payload.published,
            tenant_id=payload.tenant_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_articles(self, *, tenant_id: UUID | None = None, published_only: bool = True):
        q = self.db.query(KnowledgeArticle)
        if tenant_id is not None:
            q = q.filter(
                (KnowledgeArticle.tenant_id == tenant_id) | (KnowledgeArticle.tenant_id.is_(None))
            )
        if published_only:
            q = q.filter(KnowledgeArticle.published.is_(True))
        return q.order_by(KnowledgeArticle.updated_at.desc()).all()

    def list_runs(self, *, task_type: str | None = None, limit: int = 50):
        q = self.db.query(AIRun)
        if task_type:
            q = q.filter(AIRun.task_type == task_type)
        return q.order_by(AIRun.created_at.desc()).limit(limit).all()

    # ---- helpers ----

    @staticmethod
    def _parse_json_block(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        return {**fallback, "raw": text}

    @staticmethod
    def _heuristic_rca(req: AIRootCauseRequest) -> dict[str, Any]:
        symptoms = (req.symptoms or "").lower()
        causes = []
        if "disk" in symptoms or "space" in symptoms:
            causes.append("Storage capacity exhaustion")
        if "cpu" in symptoms or "high load" in symptoms:
            causes.append("CPU saturation / runaway process")
        if "memory" in symptoms or "oom" in symptoms:
            causes.append("Memory pressure")
        if "dns" in symptoms:
            causes.append("DNS resolution failure")
        if not causes:
            causes.append("Needs further telemetry correlation")
        return {
            "summary": f"Heuristic RCA for: {req.title}",
            "likely_causes": causes,
            "confidence": 0.45,
            "recommended_checks": [
                "Review recent alerts and change window",
                "Inspect device metrics (CPU/mem/disk)",
                "Validate network path and DNS",
            ],
        }

    @staticmethod
    def _heuristic_script(req: AIScriptRequest) -> dict[str, Any]:
        if req.platform.lower() in ("powershell", "ps1"):
            script = (
                f"# Goal: {req.goal}\n"
                "$ErrorActionPreference = 'Stop'\n"
                "Write-Output 'Starting remediation...\n"
                "# TODO: implement safe steps for environment\n"
                "Write-Output 'Done'\n"
            )
        else:
            script = f"#!/usr/bin/env bash\nset -euo pipefail\necho 'Goal: {req.goal}'\n"
        return {
            "script": script,
            "explanation": "Template script — review before production use",
            "risks": ["Always test in lab", "May require elevation"],
        }
