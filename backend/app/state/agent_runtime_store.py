"""Persist runtime agent credentials across process restarts."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

STORE = Path(os.environ.get("BHUDI_RUNTIME_STORE", "/tmp/bhudi_runtime_agents.json"))


def load_agents() -> dict[str, dict[str, Any]]:
    try:
        if not STORE.exists():
            return {}
        data = json.loads(STORE.read_text(encoding="utf-8"))
        agents = data.get("agents") or {}
        return agents if isinstance(agents, dict) else {}
    except Exception as exc:
        print(f"[runtime-store] load failed: {exc}")
        return {}


def save_agents(agents: dict[str, dict[str, Any]]) -> None:
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STORE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"agents": agents}, default=str), encoding="utf-8")
        tmp.replace(STORE)
    except Exception as exc:
        print(f"[runtime-store] save failed: {exc}")
