"""In-app Bhudi AI assistant (chat panel)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


class AssistantService:
    """Chat assistant with a live OpenAI-compatible model and honest offline fallback."""

    def __init__(self) -> None:
        self.enabled = os.getenv("AI_ENABLED", "false").lower() in ("1", "true", "yes", "on")
        self.api_key = os.getenv("AI_API_KEY", "")
        self.base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")

    def chat(self, message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        t0 = time.perf_counter()
        message = (message or "").strip()
        if not message:
            return {
                "reply": "Ask a specific question about an IT issue, device, patch, alert, print queue, or MFA failure.",
                "mode": "idle",
                "suggestions": [
                    "How should I investigate a Windows device with high CPU?",
                    "What evidence should I collect for failed patches?",
                    "Help me troubleshoot repeated MFA failures.",
                ],
                "latency_ms": 0,
            }

        turns = self._normalise_history(history or [])
        live = self._live_chat(turns, message)
        if live:
            reply, mode = live, "live"
        else:
            reply, mode = self._heuristic(message), "heuristic"

        return {
            "reply": reply,
            "mode": mode,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "suggestions": self._followups(message),
        }

    @staticmethod
    def _normalise_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
        """Keep valid, bounded conversation turns instead of flattening them into one user prompt."""
        turns: list[dict[str, str]] = []
        for turn in history[-8:]:
            if not isinstance(turn, dict):
                continue
            role = turn.get("role")
            content = turn.get("content")
            if role not in ("user", "assistant") or not isinstance(content, str):
                continue
            content = content.strip()
            if content:
                turns.append({"role": role, "content": content[:4000]})
        return turns

    def _live_chat(self, history: list[dict[str, str]], message: str) -> str | None:
        if not self.enabled or not self.api_key:
            return None

        system = (
            "You are Bhudi AI, a practical MSP and IT-operations copilot inside the Bhudi RMM portal. "
            "Give direct, useful, context-aware answers rather than generic lists. First identify the likely "
            "cause or next best diagnostic step, then give a short ordered plan, verification steps, and "
            "risks where relevant. Ask one focused clarification when the request lacks the detail needed "
            "to be accurate. Adapt to Windows, Microsoft 365/Entra, networking, endpoint security, patching, "
            "remote access, printers, alerts, and MFA. Distinguish observed facts from hypotheses. You do not "
            "have access to live tenant/device data unless it is explicitly included in the conversation; "
            "never claim to have checked a device, alert, patch state, user, or tenant when you have not. "
            "Never expose secrets or recommend destructive production changes without validation and approval. "
            "Keep answers concise (normally under 200 words), and use numbered steps when useful."
        )
        messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]
        body = {"model": self.model, "messages": messages, "temperature": 0.2}
        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            if isinstance(content, str) and content.strip():
                return content.strip()
        except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError):
            # Fall back cleanly; don't leak provider URLs, transport details, or configuration.
            return None
        except Exception:
            # Provider SDK-compatible endpoints can return unexpected payload shapes.
            return None
        return None

    def _followups(self, message: str) -> list[str]:
        m = message.lower()
        if "cpu" in m or "performance" in m:
            return ["What process is consuming the CPU?", "How do I verify whether this is sustained load?"]
        if "patch" in m or "kb" in m:
            return ["How do I validate the failed KB installation?", "What evidence belongs in a patch compliance report?"]
        if "mfa" in m or "login" in m:
            return ["How do I distinguish clock drift from a bad MFA registration?", "What sign-in logs should I inspect?"]
        if "print" in m or "spooler" in m:
            return ["How do I isolate a stuck print job?", "How do I verify the spooler recovered?"]
        if "offline" in m or "agent" in m:
            return ["How do I check agent connectivity?", "What logs should I collect before re-enrolling?"]
        return [
            "Help me build a step-by-step troubleshooting plan",
            "What evidence should I collect before remediation?",
            "How do I verify the fix without disrupting users?",
        ]

    def _heuristic(self, message: str) -> str:
        m = message.lower()
        if "cpu" in m or "performance" in m:
            return (
                "I’m in guided mode, so I can’t inspect your live device telemetry from this chat.\n\n"
                "**Start with these checks**\n"
                "1. In Bhudi, open the affected device and compare current CPU with its recent trend.\n"
                "2. Identify the top process and correlate it with AV scans, backups, updates, or a recent change.\n"
                "3. Check memory, disk queue, and event logs to distinguish CPU saturation from a wider bottleneck.\n"
                "4. Before stopping a process, confirm its owner and business impact.\n\n"
                "Share the hostname, CPU trend, and top process to narrow this down."
            )
        if "patch" in m or "kb" in m or "missing" in m:
            return (
                "I’m in guided mode and can’t see your live patch inventory.\n\n"
                "1. In Patching, identify the affected device, KB, installation result, and last scan time.\n"
                "2. Check OS/build compatibility, pending reboot, free disk space, and Windows Update error code.\n"
                "3. Retry on one representative device first, then verify the installed KB and compliance rescan.\n\n"
                "Send the KB ID and error code for a targeted troubleshooting path."
            )
        if "print" in m or "spooler" in m:
            return (
                "I’m in guided mode and can’t query your live print queues.\n\n"
                "1. Identify whether the queue, print server, or only one endpoint is affected.\n"
                "2. Capture the failed job, printer/driver, and relevant PrintService logs.\n"
                "3. Clear only the confirmed stuck job; restart the spooler only after checking impact.\n"
                "4. Submit a small test page and confirm the queue remains healthy."
            )
        if "mfa" in m or "login" in m:
            return (
                "I’m in guided mode and can’t inspect live sign-in logs.\n\n"
                "1. Capture the user, timestamp, app, correlation/request ID, and Entra sign-in error.\n"
                "2. Check Conditional Access result, authentication method, device time, and recent MFA changes.\n"
                "3. Reset MFA only after verifying identity and confirming the authenticator is lost or compromised.\n\n"
                "Share the error code (not passwords, tokens, or MFA codes) for a more specific diagnosis."
            )
        if "offline" in m or "agent" in m:
            return (
                "I’m in guided mode and can’t confirm which tenant agents are currently offline.\n\n"
                "1. Check the device’s last heartbeat and reported agent version in Bhudi.\n"
                "2. Verify the service is running and the endpoint can reach the configured API over HTTPS.\n"
                "3. Review agent logs for authentication, TLS, DNS, or repeated retry errors.\n"
                "4. Re-enrol only after preserving logs and confirming the tenant/device identity."
            )
        if "compliance" in m or "report" in m:
            return (
                "For a useful monthly operations report, include patch compliance, offline agents, critical alerts, "
                "backup outcomes, MFA/sign-in risks, reporting period, and affected-device counts. State the data "
                "source and timestamp for each metric. I can help structure the report, but I can’t claim live "
                "tenant counts unless those results are supplied to this chat."
            )
        return (
            "I’m currently in guided mode, not connected to a live model or live tenant telemetry. "
            "I can help plan troubleshooting for Windows endpoints, patching, alerts, printing, remote access, "
            "Microsoft 365/Entra, endpoint security, and MFA. Tell me the symptom, affected scope, and any error "
            "code, and I’ll give you a focused diagnostic plan.\n\n"
            "To enable model-generated answers, configure AI_ENABLED=true and AI_API_KEY on the backend service."
        )
