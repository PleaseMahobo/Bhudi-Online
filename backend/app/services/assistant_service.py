"""In-app Bhudi AI assistant (chat panel)."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any


class AssistantService:
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
                "reply": "Ask me about devices, patches, alerts, print queues, or MFA failures.",
                "mode": "idle",
                "suggestions": [
                    "Why is DC01 showing high CPU?",
                    "Show machines missing recent patches.",
                    "Which users failed MFA today?",
                ],
                "latency_ms": 0,
            }

        hist = history or []
        prior = ""
        for turn in hist[-6:]:
            prior += f"{turn.get('role', 'user')}: {turn.get('content', '')}\n"

        live = self._live_chat(prior, message)
        if live and not live.startswith(self._heuristic(message)[:40]):
            # Prefer live when we got model text that is not only heuristic fallback
            reply, mode = live, "live" if self.enabled and self.api_key else "heuristic"
            if "Live model unavailable" in live:
                mode = "heuristic"
        elif live:
            reply, mode = live, "heuristic" if "Live model unavailable" in live else "live"
        else:
            reply, mode = self._heuristic(message), "heuristic"

        return {
            "reply": reply,
            "mode": mode,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "suggestions": self._followups(message),
        }

    def _live_chat(self, prior: str, message: str) -> str | None:
        if not self.enabled or not self.api_key:
            return None
        system = (
            "You are Bhudi AI, an MSP / IT operations copilot for the Bhudi RMM platform. "
            "Answer clearly about monitoring, patching, remote access, print, security, and MFA. "
            "Keep answers under 200 words unless asked for detail."
        )
        user = f"{prior}user: {message}" if prior else message
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return str(payload["choices"][0]["message"]["content"]).strip()
        except Exception as exc:
            return f"{self._heuristic(message)}\n\n_(Live model unavailable: {exc})_"

    def _followups(self, message: str) -> list[str]:
        m = message.lower()
        if "cpu" in m or "performance" in m:
            return ["Show top processes on that host", "Open device metrics for the last hour"]
        if "patch" in m or "kb" in m:
            return ["List devices missing critical patches", "Start a patch compliance report"]
        if "mfa" in m or "login" in m:
            return ["Who failed MFA in the last 24 hours?", "How do I reset a user's MFA?"]
        if "print" in m:
            return ["Show offline printers", "Restart Print Spooler on a site"]
        return [
            "Summarize open critical alerts",
            "Which agents are offline?",
            "Draft a remediation plan for high disk usage",
        ]

    def _heuristic(self, message: str) -> str:
        m = message.lower()
        if "cpu" in m:
            return (
                "High CPU is often a runaway process, AV scan, backup job, or undersized host.\n\n"
                "**In Bhudi**\n"
                "1. **Devices** → host → **Processes**\n"
                "2. Check **Metrics** for sustained vs spike CPU\n"
                "3. **Remote** or queue a script if you need to stop the offender\n\n"
                "Tell me the hostname for a tighter checklist."
            )
        if "patch" in m or "kb" in m or "missing" in m:
            return (
                "Patch gaps live under **Patching** / device compliance.\n\n"
                "1. Open **Patching**, filter missing/critical\n"
                "2. Open the device patch/software tab\n"
                "3. Queue deploy from **Automation**\n\n"
                "Paste a KB id for a more specific pattern."
            )
        if "print" in m or "spooler" in m:
            return (
                "Use **Print Management** for queues, drivers, and offline printers.\n\n"
                "1. Offline devices / failed jobs on the print dashboard\n"
                "2. Restart Print Spooler via **Scripts** or remote command\n"
                "3. Verify driver versions and toner/paper levels"
            )
        if "mfa" in m:
            return (
                "MFA issues are usually wrong TOTP, clock skew, or an old secret after QR rotation.\n\n"
                "1. Login only needs the **current 6-digit** code after enrollment\n"
                "2. Reset MFA only if the authenticator was lost\n"
                "3. Avoid scanning multiple QR codes for the same account"
            )
        if "compliance" in m or "report" in m:
            return (
                "Build monthly packs from **Reports** / **Compliance**: "
                "patch %, offline agents, critical alerts, MFA enrollment, backup success."
            )
        if "offline" in m or "agent" in m:
            return (
                "Offline agents: **Devices** → status offline. Confirm the agent service can reach the API. "
                "Invalid credentials → delete agent_identity.json and re-enroll."
            )
        return (
            "I can help with devices, patches, alerts, print, remote access, and MFA.\n\n"
            "Try: *Why is DC01 showing high CPU?* or *Show machines missing patches.*\n\n"
            "For live LLM answers set `AI_ENABLED=true` and `AI_API_KEY` on the API service."
        )
