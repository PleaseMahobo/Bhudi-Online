"""Portal-facing agent installer download.

Proxies the latest native agent artifacts from the GitHub release tag
``agent-native-latest`` so the Bhudi portal can offer a one-click download
without sending operators to github.com.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import current_tenant_user
from app.database.session import get_db
from app.services.agent_enrollment_service import AgentEnrollmentService
from app.services.entitlement_service import EntitlementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agent Installer"])

_DEFAULT_BASE = (
    os.getenv("BHUDI_AGENT_RELEASE_BASE")
    or "https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest"
)

_ASSETS: dict[str, str] = {
    "setup": "BhudiAgent-Setup.exe",
    "msi": "bhudi-agent-setup.msi",
    "agent": "bhudi-agent.exe",
    "support": "bhudi-support.exe",
    "windows": "bhudi-agent-windows-amd64.exe",
}


def _asset_url(kind: str) -> str:
    name = _ASSETS.get(kind)
    if not name:
        raise HTTPException(status_code=400, detail=f"Unknown installer kind: {kind}")
    return f"{_DEFAULT_BASE.rstrip('/')}/{name}"


@router.get("/installer/info")
def installer_info(
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
) -> dict[str, Any]:
    """Metadata + download URLs for the portal Install Agent page."""
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="No tenant context")

    EntitlementService(db).require_download_allowed(tenant_id, user=user)

    token = None
    try:
        raw, _ = AgentEnrollmentService(db).create(tenant_id)
        token = raw
    except Exception:
        logger.exception("enrollment token for installer info failed")

    return {
        "version": os.getenv("BHUDI_AGENT_VERSION", "2.2.9"),
        "release_tag": "agent-native-latest",
        "server_url": os.getenv(
            "BHUDI_PUBLIC_API_URL",
            "https://bhudi-online-production.up.railway.app",
        ),
        "enrollment_token": token,
        "downloads": {
            "setup_exe": _asset_url("setup"),
            "msi": _asset_url("msi"),
            "agent_exe": _asset_url("agent"),
            "support_exe": _asset_url("support"),
            "portal_proxy": {
                "setup": "/api/v1/agents/installer/download?kind=setup",
                "msi": "/api/v1/agents/installer/download?kind=msi",
                "agent": "/api/v1/agents/installer/download?kind=agent",
                "support": "/api/v1/agents/installer/download?kind=support",
            },
        },
        "notes": [
            "Prefer MSI or setup EXE for agent + tray in one install.",
            "After install, confirm: bhudi-agent.exe version → 2.2.9",
            "Remote desktop requires a console user logged on to the PC.",
        ],
    }


@router.get("/installer/download")
def download_installer(
    kind: str = Query("setup", description="setup | msi | agent | support | windows"),
    mode: str = Query("redirect", description="redirect | proxy"),
    db: Session = Depends(get_db),
    user=Depends(current_tenant_user),
):
    """Download the latest agent artifact via the portal API."""
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="No tenant context")

    EntitlementService(db).require_download_allowed(tenant_id, user=user)

    url = _asset_url(kind)
    filename = _ASSETS.get(kind, _ASSETS["setup"])

    if mode == "redirect":
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    try:
        client = httpx.Client(timeout=120.0, follow_redirects=True)
        upstream = client.stream("GET", url)
        response = upstream.__enter__()
        if response.status_code != 200:
            upstream.__exit__(None, None, None)
            client.close()
            raise HTTPException(
                status_code=502,
                detail=f"Upstream release returned HTTP {response.status_code}",
            )

        def iter_bytes():
            try:
                for chunk in response.iter_bytes():
                    yield chunk
            finally:
                upstream.__exit__(None, None, None)
                client.close()

        return StreamingResponse(
            iter_bytes(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Bhudi-Agent-Source": url,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("installer download failed kind=%s", kind)
        raise HTTPException(status_code=502, detail=f"Installer download failed: {exc}") from exc
