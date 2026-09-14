"""Vendor cloud API connectors for endpoint security products.

Each connector pulls agent health and (where available) findings from the
vendor's cloud API and maps them into Bhudi ingest payloads.

Credentials live in SecurityProvider.config (never logged). Typical keys:

  CrowdStrike:   client_id, client_secret, base_url (optional)
  SentinelOne:   api_token, base_url (e.g. https://usea1.sentinelone.net)
  Huntress:      api_key, api_secret
  Bitdefender:   api_key, company_id (GravityZone)
  Sophos:        client_id, client_secret, tenant_id, data_region
  Microsoft:     tenant_id, client_id, client_secret  (Defender for Endpoint)

Connectors degrade gracefully: missing config → clear error status.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.models.endpoint_security import SecurityProvider
from app.schemas.endpoint_security import AgentIngestPayload, FindingIngestPayload
from app.services.endpoint_security_service import EndpointSecurityService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VendorSyncResult:
    def __init__(self, provider_key: str) -> None:
        self.provider_key = provider_key
        self.agents_upserted = 0
        self.findings_upserted = 0
        self.errors: list[str] = []
        self.status = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "status": self.status,
            "agents_upserted": self.agents_upserted,
            "findings_upserted": self.findings_upserted,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Individual connectors
# ---------------------------------------------------------------------------


def _sync_crowdstrike(cfg: dict[str, Any], svc: EndpointSecurityService, result: VendorSyncResult) -> None:
    client_id = cfg.get("client_id")
    client_secret = cfg.get("client_secret")
    base = (cfg.get("base_url") or "https://api.crowdstrike.com").rstrip("/")
    if not client_id or not client_secret:
        result.status = "error"
        result.errors.append("Missing client_id / client_secret in provider config")
        return

    with httpx.Client(timeout=60.0) as client:
        token_resp = client.post(
            f"{base}/oauth2/token",
            data={"client_id": client_id, "client_secret": client_secret},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"OAuth failed: HTTP {token_resp.status_code}")
            return
        access_token = token_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}

        # Device list
        devices_resp = client.get(
            f"{base}/devices/queries/devices/v1",
            params={"limit": 100},
            headers=headers,
        )
        if devices_resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"Device query failed: HTTP {devices_resp.status_code}")
            return

        device_ids = devices_resp.json().get("resources") or []
        if not device_ids:
            return

        details_resp = client.post(
            f"{base}/devices/entities/devices/v2",
            json={"ids": device_ids[:100]},
            headers=headers,
        )
        if details_resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"Device details failed: HTTP {details_resp.status_code}")
            return

        for d in details_resp.json().get("resources") or []:
            status_map = {
                "normal": "healthy",
                "containment_pending": "degraded",
                "contained": "degraded",
                "lift_containment_pending": "degraded",
            }
            status = status_map.get(str(d.get("status", "")).lower(), "unknown")
            if d.get("reduced_functionality_mode") == "yes":
                status = "degraded"

            payload = AgentIngestPayload(
                provider_key="crowdstrike",
                hostname=d.get("hostname"),
                external_agent_id=d.get("device_id"),
                agent_version=d.get("agent_version"),
                status=status,
                real_time_protection=True if status == "healthy" else None,
                last_seen_at=d.get("last_seen"),
                details={
                    "platform": d.get("platform_name"),
                    "os": d.get("os_version"),
                    "product_type": d.get("product_type_desc"),
                    "cid": d.get("cid"),
                },
            )
            try:
                svc.ingest_agent(payload)
                result.agents_upserted += 1
            except Exception as exc:
                result.errors.append(f"ingest {d.get('hostname')}: {exc}")


def _sync_sentinelone(cfg: dict[str, Any], svc: EndpointSecurityService, result: VendorSyncResult) -> None:
    token = cfg.get("api_token")
    base = (cfg.get("base_url") or "").rstrip("/")
    if not token or not base:
        result.status = "error"
        result.errors.append("Missing api_token / base_url in provider config")
        return

    headers = {"Authorization": f"ApiToken {token}"}
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(
            f"{base}/web/api/v2.1/agents",
            params={"limit": 100},
            headers=headers,
        )
        if resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"Agents list failed: HTTP {resp.status_code}")
            return

        for a in (resp.json().get("data") or []):
            is_active = bool(a.get("isActive"))
            infected = bool(a.get("infected"))
            status = "healthy" if is_active and not infected else ("degraded" if is_active else "offline")

            payload = AgentIngestPayload(
                provider_key="sentinelone",
                hostname=a.get("computerName"),
                external_agent_id=str(a.get("id") or ""),
                agent_version=a.get("agentVersion"),
                status=status,
                real_time_protection=is_active,
                last_seen_at=a.get("lastActiveDate"),
                details={
                    "os": a.get("osName"),
                    "site": a.get("siteName"),
                    "infected": infected,
                    "network_status": a.get("networkStatus"),
                },
            )
            try:
                svc.ingest_agent(payload)
                result.agents_upserted += 1
            except Exception as exc:
                result.errors.append(f"ingest {a.get('computerName')}: {exc}")


def _sync_huntress(cfg: dict[str, Any], svc: EndpointSecurityService, result: VendorSyncResult) -> None:
    api_key = cfg.get("api_key")
    api_secret = cfg.get("api_secret")
    base = (cfg.get("base_url") or "https://api.huntress.io").rstrip("/")
    if not api_key or not api_secret:
        result.status = "error"
        result.errors.append("Missing api_key / api_secret in provider config")
        return

    with httpx.Client(timeout=60.0, auth=(api_key, api_secret)) as client:
        resp = client.get(f"{base}/v1/agents", params={"limit": 100})
        if resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"Agents list failed: HTTP {resp.status_code}")
            return

        data = resp.json()
        agents = data.get("agents") or data.get("data") or []
        for a in agents:
            status_raw = str(a.get("status") or a.get("health") or "").lower()
            status = "healthy" if status_raw in {"online", "healthy", "ok"} else (
                "degraded" if status_raw else "unknown"
            )
            payload = AgentIngestPayload(
                provider_key="huntress",
                hostname=a.get("hostname") or a.get("name"),
                external_agent_id=str(a.get("id") or ""),
                agent_version=a.get("version") or a.get("agent_version"),
                status=status,
                real_time_protection=status == "healthy",
                last_seen_at=a.get("last_seen_at") or a.get("updated_at"),
                details=a,
            )
            try:
                svc.ingest_agent(payload)
                result.agents_upserted += 1
            except Exception as exc:
                result.errors.append(f"ingest: {exc}")


def _sync_bitdefender(cfg: dict[str, Any], svc: EndpointSecurityService, result: VendorSyncResult) -> None:
    api_key = cfg.get("api_key")
    company_id = cfg.get("company_id")
    base = (cfg.get("base_url") or "https://cloud.gravityzone.bitdefender.com").rstrip("/")
    if not api_key:
        result.status = "error"
        result.errors.append("Missing api_key in provider config")
        return

    # GravityZone uses Basic auth with API key as username and empty password
    with httpx.Client(timeout=60.0, auth=(api_key, "")) as client:
        body: dict[str, Any] = {
            "params": {"page": 1, "perPage": 100},
            "jsonrpc": "2.0",
            "method": "getEndpointsList",
            "id": "bhudi-1",
        }
        if company_id:
            body["params"]["parentId"] = company_id

        resp = client.post(f"{base}/api/v1.0/jsonrpc/network", json=body)
        if resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"Endpoints list failed: HTTP {resp.status_code}")
            return

        result_block = resp.json().get("result") or {}
        items = result_block.get("items") or []
        for a in items:
            is_online = bool(a.get("isOnline") or a.get("online"))
            status = "healthy" if is_online else "offline"
            payload = AgentIngestPayload(
                provider_key="bitdefender",
                hostname=a.get("name") or a.get("hostname"),
                external_agent_id=str(a.get("id") or ""),
                agent_version=a.get("agent") and a["agent"].get("productVersion"),
                status=status,
                real_time_protection=is_online,
                details=a,
            )
            try:
                svc.ingest_agent(payload)
                result.agents_upserted += 1
            except Exception as exc:
                result.errors.append(f"ingest: {exc}")


def _sync_sophos(cfg: dict[str, Any], svc: EndpointSecurityService, result: VendorSyncResult) -> None:
    client_id = cfg.get("client_id")
    client_secret = cfg.get("client_secret")
    tenant_id = cfg.get("tenant_id")
    region = cfg.get("data_region") or "us-west-2"
    if not client_id or not client_secret or not tenant_id:
        result.status = "error"
        result.errors.append("Missing client_id / client_secret / tenant_id")
        return

    with httpx.Client(timeout=60.0) as client:
        token_resp = client.post(
            "https://id.sophos.com/api/v2/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "token",
            },
        )
        if token_resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"OAuth failed: HTTP {token_resp.status_code}")
            return
        access_token = token_resp.json().get("access_token")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": tenant_id,
        }
        base = f"https://api-{region}.central.sophos.com"
        resp = client.get(f"{base}/endpoint/v1/endpoints", headers=headers, params={"pageSize": 100})
        if resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"Endpoints failed: HTTP {resp.status_code}")
            return

        for a in resp.json().get("items") or []:
            health = str((a.get("health") or {}).get("overall") or "").lower()
            status = "healthy" if health in {"good", "ok"} else ("degraded" if health else "unknown")
            payload = AgentIngestPayload(
                provider_key="sophos",
                hostname=a.get("hostname"),
                external_agent_id=a.get("id"),
                agent_version=(a.get("software") or {}).get("agentVersion"),
                status=status,
                real_time_protection=status == "healthy",
                last_seen_at=a.get("lastSeenAt"),
                details=a,
            )
            try:
                svc.ingest_agent(payload)
                result.agents_upserted += 1
            except Exception as exc:
                result.errors.append(f"ingest: {exc}")


def _sync_microsoft_defender_xdr(cfg: dict[str, Any], svc: EndpointSecurityService, result: VendorSyncResult) -> None:
    tenant_id = cfg.get("tenant_id")
    client_id = cfg.get("client_id")
    client_secret = cfg.get("client_secret")
    if not tenant_id or not client_id or not client_secret:
        result.status = "error"
        result.errors.append("Missing tenant_id / client_id / client_secret")
        return

    with httpx.Client(timeout=60.0) as client:
        token_resp = client.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://api.securitycenter.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )
        if token_resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"OAuth failed: HTTP {token_resp.status_code}")
            return
        access_token = token_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}

        resp = client.get(
            "https://api.securitycenter.microsoft.com/api/machines",
            headers=headers,
            params={"$top": 100},
        )
        if resp.status_code >= 400:
            result.status = "error"
            result.errors.append(f"Machines failed: HTTP {resp.status_code}")
            return

        for m in resp.json().get("value") or []:
            health = str(m.get("healthStatus") or "").lower()
            status = "healthy" if health == "active" else (
                "offline" if health in {"inactive", "impairedcommunication"} else "degraded"
            )
            payload = AgentIngestPayload(
                provider_key="microsoft_defender_xdr",
                hostname=m.get("computerDnsName") or m.get("hostName"),
                external_agent_id=m.get("id"),
                agent_version=m.get("agentVersion"),
                status=status,
                real_time_protection=health == "active",
                last_seen_at=m.get("lastSeen"),
                details={
                    "os": m.get("osPlatform"),
                    "rbac_group": m.get("rbacGroupName"),
                    "risk_score": m.get("riskScore"),
                },
            )
            try:
                svc.ingest_agent(payload)
                result.agents_upserted += 1
            except Exception as exc:
                result.errors.append(f"ingest: {exc}")


CONNECTORS = {
    "crowdstrike": _sync_crowdstrike,
    "sentinelone": _sync_sentinelone,
    "huntress": _sync_huntress,
    "bitdefender": _sync_bitdefender,
    "sophos": _sync_sophos,
    "microsoft_defender_xdr": _sync_microsoft_defender_xdr,
}


def sync_provider(db: Session, provider: SecurityProvider) -> VendorSyncResult:
    """Run cloud sync for a single configured provider."""
    result = VendorSyncResult(provider.provider_key)
    fn = CONNECTORS.get(provider.provider_key)
    if not fn:
        result.status = "skipped"
        result.errors.append(
            f"No cloud connector for '{provider.provider_key}' "
            "(agent-side detection still works)"
        )
        provider.last_sync_status = "skipped"
        provider.last_sync_error = result.errors[0]
        provider.last_sync_at = _utcnow()
        db.commit()
        return result

    if not provider.enabled:
        result.status = "skipped"
        result.errors.append("Provider is disabled")
        return result

    cfg = provider.config or {}
    svc = EndpointSecurityService(db)
    try:
        fn(cfg, svc, result)
        if result.errors and result.agents_upserted == 0:
            result.status = "error"
        elif result.errors:
            result.status = "partial"
        provider.last_sync_status = result.status
        provider.last_sync_error = "; ".join(result.errors[:3]) if result.errors else None
        provider.last_sync_at = _utcnow()
        db.commit()
    except Exception as exc:
        logger.exception("Vendor sync failed for %s", provider.provider_key)
        result.status = "error"
        result.errors.append(str(exc))
        provider.last_sync_status = "error"
        provider.last_sync_error = str(exc)[:500]
        provider.last_sync_at = _utcnow()
        db.commit()
    return result


def sync_all_enabled(db: Session, tenant_id: UUID | None = None) -> list[dict[str, Any]]:
    svc = EndpointSecurityService(db)
    providers = svc.list_providers(enabled_only=True, tenant_id=tenant_id)
    results = []
    for p in providers:
        if p.provider_key in CONNECTORS:
            results.append(sync_provider(db, p).to_dict())
    return results
