from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.itsm import ServiceTicket
from app.models.psa import PSA_PROVIDERS, PSAConnection, PSASyncEvent, PSATicketLink
from app.schemas.psa import (
    PSAConnectionCreate,
    PSAConnectionTestResult,
    PSAConnectionUpdate,
    PSATicketPushRequest,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


PROVIDER_CATALOG: list[dict[str, Any]] = [
    {
        "provider_key": "autotask",
        "display_name": "Autotask PSA",
        "auth_modes": ["api_integration_code", "username_password"],
        "docs_url": "https://ww1.autotask.net/help/DeveloperHelp/Content/APIs/REST/REST_API_Home.htm",
        "required_config": ["base_url", "username", "secret", "integration_code"],
    },
    {
        "provider_key": "halopsa",
        "display_name": "HaloPSA",
        "auth_modes": ["client_credentials", "api_key"],
        "docs_url": "https://haloitsm.com/apidoc/",
        "required_config": ["base_url", "client_id", "client_secret"],
    },
    {
        "provider_key": "connectwise",
        "display_name": "ConnectWise PSA",
        "auth_modes": ["api_keys"],
        "docs_url": "https://developer.connectwise.com/",
        "required_config": ["base_url", "company_id", "public_key", "private_key", "client_id"],
    },
    {
        "provider_key": "freshservice",
        "display_name": "Freshservice",
        "auth_modes": ["api_key"],
        "docs_url": "https://api.freshservice.com/",
        "required_config": ["base_url", "api_key"],
    },
    {
        "provider_key": "jira",
        "display_name": "Jira Service Management",
        "auth_modes": ["basic_api_token", "oauth"],
        "docs_url": "https://developer.atlassian.com/cloud/jira/service-desk/",
        "required_config": ["base_url", "email", "api_token", "project_key"],
    },
    {
        "provider_key": "zendesk",
        "display_name": "Zendesk",
        "auth_modes": ["api_token"],
        "docs_url": "https://developer.zendesk.com/api-reference/",
        "required_config": ["base_url", "email", "api_token"],
    },
    {
        "provider_key": "servicenow",
        "display_name": "ServiceNow",
        "auth_modes": ["basic", "oauth"],
        "docs_url": "https://developer.servicenow.com/",
        "required_config": ["base_url", "username", "password"],
    },
]


class PSAAdapterError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _cfg(conn: PSAConnection) -> dict[str, Any]:
    return dict(conn.config or {})


def _is_dry_run(cfg: dict[str, Any]) -> bool:
    if cfg.get("dry_run") is True:
        return True
    # No base_url configured → local dry-run (safe default for MSP lab installs)
    return not bool(str(cfg.get("base_url") or "").strip())


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any] | list[Any] | None, str]:
    data = None
    hdrs = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed: dict[str, Any] | list[Any] | None = None
            if raw.strip():
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
            return int(resp.status), parsed, raw
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise PSAAdapterError(
            f"HTTP {e.code} from {url}: {err_body[:500]}", status_code=e.code
        ) from e
    except urllib.error.URLError as e:
        raise PSAAdapterError(f"Network error calling {url}: {e.reason}") from e


def _basic_auth(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


class BasePSAAdapter:
    provider_key: str = "base"

    def __init__(self, conn: PSAConnection):
        self.conn = conn
        self.cfg = _cfg(conn)

    def test_connection(self) -> PSAConnectionTestResult:
        if _is_dry_run(self.cfg):
            return PSAConnectionTestResult(
                ok=True,
                provider_key=self.provider_key,
                message="Dry-run OK (no base_url / dry_run=true)",
                dry_run=True,
            )
        return self._test_live()

    def _test_live(self) -> PSAConnectionTestResult:
        raise NotImplementedError

    def create_ticket(self, ticket: ServiceTicket) -> dict[str, Any]:
        if _is_dry_run(self.cfg):
            ext_id = f"dry_{self.provider_key}_{ticket.number}_{secrets.token_hex(3)}"
            return {
                "external_id": ext_id,
                "external_key": ticket.number,
                "external_url": None,
                "external_status": "open",
                "dry_run": True,
                "raw": {"simulated": True},
            }
        return self._create_ticket_live(ticket)

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        raise NotImplementedError

    def update_ticket_status(
        self, external_id: str, status: str, *, resolution: str | None = None
    ) -> dict[str, Any]:
        if _is_dry_run(self.cfg):
            return {
                "external_id": external_id,
                "external_status": status,
                "dry_run": True,
            }
        return self._update_status_live(external_id, status, resolution=resolution)

    def _update_status_live(
        self, external_id: str, status: str, *, resolution: str | None = None
    ) -> dict[str, Any]:
        # Best-effort default; providers override when supported.
        return {"external_id": external_id, "external_status": status, "skipped": True}


class AutotaskAdapter(BasePSAAdapter):
    provider_key = "autotask"

    def _headers(self) -> dict[str, str]:
        return {
            "ApiIntegrationCode": str(self.cfg.get("integration_code") or ""),
            "UserName": str(self.cfg.get("username") or ""),
            "Secret": str(self.cfg.get("secret") or ""),
        }

    def _test_live(self) -> PSAConnectionTestResult:
        base = str(self.cfg["base_url"]).rstrip("/")
        code, _, _ = _http_json("GET", f"{base}/V1.0/ZoneInformation", headers=self._headers())
        return PSAConnectionTestResult(
            ok=200 <= code < 300,
            provider_key=self.provider_key,
            message=f"Autotask zone info HTTP {code}",
            details={"http_status": code},
        )

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        base = str(self.cfg["base_url"]).rstrip("/")
        body = {
            "title": ticket.title[:255],
            "description": ticket.description or ticket.title,
            "priority": self.cfg.get("priority_map", {}).get(ticket.priority, 3),
            "status": self.cfg.get("default_status", 1),
            "queueID": self.cfg.get("queue_id"),
            "companyID": self.cfg.get("company_id"),
        }
        body = {k: v for k, v in body.items() if v is not None}
        code, parsed, raw = _http_json(
            "POST", f"{base}/V1.0/Tickets", headers=self._headers(), body=body
        )
        item = (parsed or {}).get("item") if isinstance(parsed, dict) else None
        ext_id = str((item or {}).get("id") or (parsed or {}).get("id") or "")
        if not ext_id:
            raise PSAAdapterError(f"Autotask create missing id: {raw[:300]}")
        return {
            "external_id": ext_id,
            "external_key": ticket.number,
            "external_url": None,
            "external_status": str((item or {}).get("status") or "open"),
            "raw": parsed,
        }


class HaloPSAAdapter(BasePSAAdapter):
    provider_key = "halopsa"

    def _token(self) -> str:
        if self.cfg.get("api_key"):
            return str(self.cfg["api_key"])
        base = str(self.cfg["base_url"]).rstrip("/")
        body = {
            "grant_type": "client_credentials",
            "client_id": self.cfg.get("client_id"),
            "client_secret": self.cfg.get("client_secret"),
            "scope": self.cfg.get("scope", "all"),
        }
        # Halo token endpoint expects form body; send JSON fallback for lab mocks
        code, parsed, raw = _http_json(
            "POST",
            f"{base}/auth/token",
            headers={"Content-Type": "application/json"},
            body=body,
        )
        if not isinstance(parsed, dict) or not parsed.get("access_token"):
            raise PSAAdapterError(f"Halo token failed HTTP {code}: {raw[:300]}")
        return str(parsed["access_token"])

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token()}"}

    def _test_live(self) -> PSAConnectionTestResult:
        base = str(self.cfg["base_url"]).rstrip("/")
        code, _, _ = _http_json("GET", f"{base}/api/Status", headers=self._headers())
        return PSAConnectionTestResult(
            ok=200 <= code < 300,
            provider_key=self.provider_key,
            message=f"HaloPSA status HTTP {code}",
            details={"http_status": code},
        )

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        base = str(self.cfg["base_url"]).rstrip("/")
        body = {
            "summary": ticket.title,
            "details": ticket.description or ticket.title,
            "tickettype_id": self.cfg.get("ticket_type_id"),
            "priority_id": self.cfg.get("priority_map", {}).get(ticket.priority),
            "client_id": self.cfg.get("client_id_entity"),
        }
        body = {k: v for k, v in body.items() if v is not None}
        code, parsed, raw = _http_json(
            "POST", f"{base}/api/Tickets", headers=self._headers(), body=body
        )
        ext_id = str((parsed or {}).get("id") or (parsed or {}).get("Id") or "")
        if not ext_id:
            raise PSAAdapterError(f"Halo create missing id: {raw[:300]}")
        return {
            "external_id": ext_id,
            "external_key": str((parsed or {}).get("id") or ticket.number),
            "external_url": None,
            "external_status": str((parsed or {}).get("status_id") or "open"),
            "raw": parsed,
        }


class ConnectWiseAdapter(BasePSAAdapter):
    provider_key = "connectwise"

    def _headers(self) -> dict[str, str]:
        company = str(self.cfg.get("company_id") or "")
        public = str(self.cfg.get("public_key") or "")
        private = str(self.cfg.get("private_key") or "")
        client_id = str(self.cfg.get("client_id") or "")
        return {
            "Authorization": _basic_auth(f"{company}+{public}", private),
            "clientId": client_id,
        }

    def _test_live(self) -> PSAConnectionTestResult:
        base = str(self.cfg["base_url"]).rstrip("/")
        code, _, _ = _http_json(
            "GET", f"{base}/system/info", headers=self._headers()
        )
        return PSAConnectionTestResult(
            ok=200 <= code < 300,
            provider_key=self.provider_key,
            message=f"ConnectWise system info HTTP {code}",
            details={"http_status": code},
        )

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        base = str(self.cfg["base_url"]).rstrip("/")
        body = {
            "summary": ticket.title[:100],
            "initialDescription": ticket.description or ticket.title,
            "company": {"id": self.cfg.get("company_record_id")},
            "board": {"id": self.cfg.get("board_id")},
            "priority": {"id": self.cfg.get("priority_map", {}).get(ticket.priority)},
        }
        # strip empty nested ids
        if not body["company"]["id"]:
            body.pop("company")
        if not body.get("board", {}).get("id"):
            body.pop("board", None)
        if not body.get("priority", {}).get("id"):
            body.pop("priority", None)
        code, parsed, raw = _http_json(
            "POST", f"{base}/service/tickets", headers=self._headers(), body=body
        )
        ext_id = str((parsed or {}).get("id") or "")
        if not ext_id:
            raise PSAAdapterError(f"ConnectWise create missing id: {raw[:300]}")
        return {
            "external_id": ext_id,
            "external_key": str((parsed or {}).get("id")),
            "external_url": None,
            "external_status": str(
                ((parsed or {}).get("status") or {}).get("name") or "open"
            ),
            "raw": parsed,
        }


class FreshserviceAdapter(BasePSAAdapter):
    provider_key = "freshservice"

    def _headers(self) -> dict[str, str]:
        key = str(self.cfg.get("api_key") or "")
        return {"Authorization": _basic_auth(key, "X")}

    def _test_live(self) -> PSAConnectionTestResult:
        base = str(self.cfg["base_url"]).rstrip("/")
        code, _, _ = _http_json("GET", f"{base}/api/v2/tickets?per_page=1", headers=self._headers())
        return PSAConnectionTestResult(
            ok=200 <= code < 300,
            provider_key=self.provider_key,
            message=f"Freshservice tickets HTTP {code}",
            details={"http_status": code},
        )

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        base = str(self.cfg["base_url"]).rstrip("/")
        priority_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        body = {
            "email": self.cfg.get("requester_email") or "msp@example.com",
            "subject": ticket.title,
            "description": ticket.description or ticket.title,
            "priority": priority_map.get(ticket.priority, 2),
            "status": 2,
        }
        code, parsed, raw = _http_json(
            "POST", f"{base}/api/v2/tickets", headers=self._headers(), body=body
        )
        t = (parsed or {}).get("ticket") if isinstance(parsed, dict) else None
        ext_id = str((t or {}).get("id") or "")
        if not ext_id:
            raise PSAAdapterError(f"Freshservice create missing id: {raw[:300]}")
        return {
            "external_id": ext_id,
            "external_key": str((t or {}).get("id")),
            "external_url": None,
            "external_status": str((t or {}).get("status") or "open"),
            "raw": parsed,
        }


class JiraAdapter(BasePSAAdapter):
    provider_key = "jira"

    def _headers(self) -> dict[str, str]:
        email = str(self.cfg.get("email") or "")
        token = str(self.cfg.get("api_token") or "")
        return {"Authorization": _basic_auth(email, token)}

    def _test_live(self) -> PSAConnectionTestResult:
        base = str(self.cfg["base_url"]).rstrip("/")
        code, _, _ = _http_json("GET", f"{base}/rest/api/3/myself", headers=self._headers())
        return PSAConnectionTestResult(
            ok=200 <= code < 300,
            provider_key=self.provider_key,
            message=f"Jira myself HTTP {code}",
            details={"http_status": code},
        )

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        base = str(self.cfg["base_url"]).rstrip("/")
        project = str(self.cfg.get("project_key") or "SUP")
        issue_type = str(self.cfg.get("issue_type") or "Task")
        body = {
            "fields": {
                "project": {"key": project},
                "summary": ticket.title,
                "description": ticket.description or ticket.title,
                "issuetype": {"name": issue_type},
            }
        }
        code, parsed, raw = _http_json(
            "POST", f"{base}/rest/api/3/issue", headers=self._headers(), body=body
        )
        ext_id = str((parsed or {}).get("id") or "")
        key = str((parsed or {}).get("key") or "")
        if not ext_id:
            raise PSAAdapterError(f"Jira create missing id: {raw[:300]}")
        return {
            "external_id": ext_id,
            "external_key": key or ticket.number,
            "external_url": f"{base}/browse/{key}" if key else None,
            "external_status": "open",
            "raw": parsed,
        }


class ZendeskAdapter(BasePSAAdapter):
    provider_key = "zendesk"

    def _headers(self) -> dict[str, str]:
        email = str(self.cfg.get("email") or "")
        token = str(self.cfg.get("api_token") or "")
        return {"Authorization": _basic_auth(f"{email}/token", token)}

    def _test_live(self) -> PSAConnectionTestResult:
        base = str(self.cfg["base_url"]).rstrip("/")
        code, _, _ = _http_json("GET", f"{base}/api/v2/users/me.json", headers=self._headers())
        return PSAConnectionTestResult(
            ok=200 <= code < 300,
            provider_key=self.provider_key,
            message=f"Zendesk me HTTP {code}",
            details={"http_status": code},
        )

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        base = str(self.cfg["base_url"]).rstrip("/")
        body = {
            "ticket": {
                "subject": ticket.title,
                "comment": {"body": ticket.description or ticket.title},
                "priority": ticket.priority if ticket.priority in ("low", "normal", "high", "urgent") else "normal",
            }
        }
        code, parsed, raw = _http_json(
            "POST", f"{base}/api/v2/tickets.json", headers=self._headers(), body=body
        )
        t = (parsed or {}).get("ticket") if isinstance(parsed, dict) else None
        ext_id = str((t or {}).get("id") or "")
        if not ext_id:
            raise PSAAdapterError(f"Zendesk create missing id: {raw[:300]}")
        return {
            "external_id": ext_id,
            "external_key": str((t or {}).get("id")),
            "external_url": f"{base}/agent/tickets/{ext_id}",
            "external_status": str((t or {}).get("status") or "new"),
            "raw": parsed,
        }


class ServiceNowAdapter(BasePSAAdapter):
    provider_key = "servicenow"

    def _headers(self) -> dict[str, str]:
        user = str(self.cfg.get("username") or "")
        password = str(self.cfg.get("password") or "")
        return {"Authorization": _basic_auth(user, password)}

    def _test_live(self) -> PSAConnectionTestResult:
        base = str(self.cfg["base_url"]).rstrip("/")
        code, _, _ = _http_json(
            "GET",
            f"{base}/api/now/table/incident?sysparm_limit=1",
            headers=self._headers(),
        )
        return PSAConnectionTestResult(
            ok=200 <= code < 300,
            provider_key=self.provider_key,
            message=f"ServiceNow incident table HTTP {code}",
            details={"http_status": code},
        )

    def _create_ticket_live(self, ticket: ServiceTicket) -> dict[str, Any]:
        base = str(self.cfg["base_url"]).rstrip("/")
        table = str(self.cfg.get("table") or "incident")
        urgency_map = {"low": "3", "medium": "2", "high": "1", "critical": "1"}
        body = {
            "short_description": ticket.title,
            "description": ticket.description or ticket.title,
            "urgency": urgency_map.get(ticket.priority, "2"),
            "impact": urgency_map.get(ticket.impact or ticket.priority, "2"),
            "caller_id": self.cfg.get("caller_id"),
            "assignment_group": self.cfg.get("assignment_group"),
        }
        body = {k: v for k, v in body.items() if v is not None}
        code, parsed, raw = _http_json(
            "POST",
            f"{base}/api/now/table/{table}",
            headers=self._headers(),
            body=body,
        )
        result = (parsed or {}).get("result") if isinstance(parsed, dict) else None
        ext_id = str((result or {}).get("sys_id") or "")
        number = str((result or {}).get("number") or "")
        if not ext_id:
            raise PSAAdapterError(f"ServiceNow create missing sys_id: {raw[:300]}")
        return {
            "external_id": ext_id,
            "external_key": number or ticket.number,
            "external_url": f"{base}/nav_to.do?uri={table}.do?sys_id={ext_id}",
            "external_status": str((result or {}).get("state") or "open"),
            "raw": parsed,
        }


ADAPTERS: dict[str, type[BasePSAAdapter]] = {
    "autotask": AutotaskAdapter,
    "halopsa": HaloPSAAdapter,
    "connectwise": ConnectWiseAdapter,
    "freshservice": FreshserviceAdapter,
    "jira": JiraAdapter,
    "zendesk": ZendeskAdapter,
    "servicenow": ServiceNowAdapter,
}


def get_adapter(conn: PSAConnection) -> BasePSAAdapter:
    cls = ADAPTERS.get(conn.provider_key)
    if not cls:
        raise ValueError(f"Unsupported PSA provider: {conn.provider_key}")
    return cls(conn)


class PSAService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_catalog(self) -> list[dict[str, Any]]:
        return list(PROVIDER_CATALOG)

    def seed_connections(self, tenant_id: UUID | None = None) -> list[PSAConnection]:
        created: list[PSAConnection] = []
        for item in PROVIDER_CATALOG:
            q = self.db.query(PSAConnection).filter(
                PSAConnection.provider_key == item["provider_key"]
            )
            if tenant_id:
                q = q.filter(PSAConnection.tenant_id == tenant_id)
            else:
                q = q.filter(PSAConnection.tenant_id.is_(None))
            if q.first():
                continue
            row = PSAConnection(
                provider_key=item["provider_key"],
                display_name=item["display_name"],
                enabled=False,
                tenant_id=tenant_id,
                config={"dry_run": True},
                last_sync_status="never",
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        for r in created:
            self.db.refresh(r)
        return created

    def create_connection(self, payload: PSAConnectionCreate) -> PSAConnection:
        key = payload.provider_key.strip().lower()
        if key not in PSA_PROVIDERS:
            raise ValueError(
                f"Unsupported provider_key '{key}'. Allowed: {', '.join(PSA_PROVIDERS)}"
            )
        row = PSAConnection(
            provider_key=key,
            display_name=payload.display_name,
            enabled=payload.enabled,
            tenant_id=payload.tenant_id,
            config=payload.config,
            webhook_secret=payload.webhook_secret,
            notes=payload.notes,
            last_sync_status="never",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_connections(
        self, *, enabled_only: bool = False, tenant_id: UUID | None = None
    ) -> list[PSAConnection]:
        q = self.db.query(PSAConnection)
        if enabled_only:
            q = q.filter(PSAConnection.enabled.is_(True))
        if tenant_id is not None:
            q = q.filter(PSAConnection.tenant_id == tenant_id)
        return q.order_by(PSAConnection.display_name.asc()).all()

    def get_connection(self, connection_id: UUID) -> PSAConnection | None:
        return self.db.get(PSAConnection, connection_id)

    def update_connection(
        self, connection_id: UUID, payload: PSAConnectionUpdate
    ) -> PSAConnection | None:
        row = self.get_connection(connection_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_connection(self, connection_id: UUID) -> bool:
        row = self.get_connection(connection_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def test_connection(self, connection_id: UUID) -> PSAConnectionTestResult:
        row = self.get_connection(connection_id)
        if not row:
            raise ValueError("Connection not found")
        adapter = get_adapter(row)
        try:
            result = adapter.test_connection()
            row.last_tested_at = _utcnow()
            row.last_sync_status = "ok" if result.ok else "error"
            row.last_sync_error = None if result.ok else result.message
            self.db.commit()
            return result
        except PSAAdapterError as e:
            row.last_tested_at = _utcnow()
            row.last_sync_status = "error"
            row.last_sync_error = str(e)
            self.db.commit()
            return PSAConnectionTestResult(
                ok=False,
                provider_key=row.provider_key,
                message=str(e),
                dry_run=_is_dry_run(_cfg(row)),
            )

    def push_ticket(self, payload: PSATicketPushRequest) -> PSATicketLink:
        conn = self.get_connection(payload.connection_id)
        if not conn:
            raise ValueError("Connection not found")
        if not conn.enabled:
            raise ValueError("Connection is disabled")

        ticket = self.db.get(ServiceTicket, payload.ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")

        existing = (
            self.db.query(PSATicketLink)
            .filter(
                PSATicketLink.connection_id == conn.id,
                PSATicketLink.ticket_id == ticket.id,
            )
            .first()
        )
        if existing and not payload.force:
            return existing

        adapter = get_adapter(conn)
        event = PSASyncEvent(
            connection_id=conn.id,
            event_type="push",
            direction="outbound",
            status="received",
            payload={"ticket_id": str(ticket.id), "number": ticket.number},
        )
        self.db.add(event)
        self.db.flush()

        try:
            result = adapter.create_ticket(ticket)
            if existing:
                link = existing
                link.external_id = result["external_id"]
                link.external_key = result.get("external_key")
                link.external_url = result.get("external_url")
                link.external_status = result.get("external_status")
                link.sync_status = "linked"
                link.last_error = None
                link.last_synced_at = _utcnow()
                link.metadata_json = {"raw": result.get("raw"), "dry_run": result.get("dry_run")}
            else:
                link = PSATicketLink(
                    connection_id=conn.id,
                    ticket_id=ticket.id,
                    external_id=result["external_id"],
                    external_key=result.get("external_key"),
                    external_url=result.get("external_url"),
                    external_status=result.get("external_status"),
                    direction="outbound",
                    sync_status="linked",
                    last_synced_at=_utcnow(),
                    metadata_json={
                        "raw": result.get("raw"),
                        "dry_run": result.get("dry_run"),
                    },
                )
                self.db.add(link)

            event.status = "processed"
            event.action = f"pushed ticket {ticket.number} → {result['external_id']}"
            event.external_ticket_id = result["external_id"]
            event.processed_at = _utcnow()
            conn.last_sync_at = _utcnow()
            conn.last_sync_status = "ok"
            conn.last_sync_error = None
            self.db.commit()
            self.db.refresh(link)
            return link
        except Exception as e:
            event.status = "error"
            event.error = str(e)
            event.processed_at = _utcnow()
            conn.last_sync_status = "error"
            conn.last_sync_error = str(e)
            self.db.commit()
            raise

    def list_links(
        self,
        *,
        connection_id: UUID | None = None,
        ticket_id: UUID | None = None,
    ) -> list[PSATicketLink]:
        q = self.db.query(PSATicketLink).options(joinedload(PSATicketLink.connection))
        if connection_id:
            q = q.filter(PSATicketLink.connection_id == connection_id)
        if ticket_id:
            q = q.filter(PSATicketLink.ticket_id == ticket_id)
        return q.order_by(PSATicketLink.created_at.desc()).all()

    def list_events(
        self,
        *,
        connection_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[PSASyncEvent]:
        q = self.db.query(PSASyncEvent)
        if connection_id:
            q = q.filter(PSASyncEvent.connection_id == connection_id)
        if status:
            q = q.filter(PSASyncEvent.status == status)
        return q.order_by(PSASyncEvent.received_at.desc()).limit(limit).all()

    def verify_webhook_signature(
        self, conn: PSAConnection, payload: bytes, signature: str | None
    ) -> bool:
        secret = conn.webhook_secret
        if not secret:
            return True  # open if not configured
        if not signature:
            return False
        digest = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        candidates = {digest, f"sha256={digest}"}
        # some providers send hex only or prefixed
        sig = signature.strip()
        if sig.startswith("sha256="):
            return hmac.compare_digest(sig, f"sha256={digest}")
        return any(hmac.compare_digest(sig, c) for c in candidates)

    def process_webhook(
        self,
        connection_id: UUID,
        payload: dict[str, Any],
        *,
        external_event_id: str | None = None,
        signature: str | None = None,
        raw_body: bytes | None = None,
    ) -> dict[str, Any]:
        conn = self.get_connection(connection_id)
        if not conn:
            raise ValueError("Connection not found")
        if not conn.enabled:
            raise ValueError("Connection is disabled")

        if raw_body is not None and not self.verify_webhook_signature(
            conn, raw_body, signature
        ):
            raise ValueError("Invalid webhook signature")

        # Normalize common fields across providers
        event_type = str(
            payload.get("event_type")
            or payload.get("type")
            or payload.get("event")
            or "ticket.updated"
        )
        ext_ticket = (
            payload.get("external_ticket_id")
            or payload.get("ticket_id")
            or (payload.get("ticket") or {}).get("id")
            or (payload.get("data") or {}).get("id")
        )
        ext_ticket_s = str(ext_ticket) if ext_ticket is not None else None
        ext_event = external_event_id or payload.get("id") or payload.get("event_id")
        ext_event_s = str(ext_event) if ext_event is not None else None

        if ext_event_s:
            dup = (
                self.db.query(PSASyncEvent)
                .filter(
                    PSASyncEvent.connection_id == conn.id,
                    PSASyncEvent.external_event_id == ext_event_s,
                )
                .first()
            )
            if dup:
                return {
                    "status": "duplicate",
                    "action": dup.action,
                    "event_id": dup.id,
                    "duplicate": True,
                }

        event = PSASyncEvent(
            connection_id=conn.id,
            event_type=event_type[:64],
            direction="inbound",
            external_event_id=ext_event_s,
            external_ticket_id=ext_ticket_s,
            status="received",
            payload=payload,
        )
        self.db.add(event)
        self.db.flush()

        action = "ignored"
        try:
            if ext_ticket_s:
                link = (
                    self.db.query(PSATicketLink)
                    .filter(
                        PSATicketLink.connection_id == conn.id,
                        PSATicketLink.external_id == ext_ticket_s,
                    )
                    .first()
                )
                new_status = (
                    payload.get("status")
                    or (payload.get("ticket") or {}).get("status")
                    or payload.get("external_status")
                )
                if link and new_status:
                    link.external_status = str(new_status)
                    link.last_synced_at = _utcnow()
                    # Map closed-like statuses onto internal ticket when linked
                    internal = self.db.get(ServiceTicket, link.ticket_id)
                    status_l = str(new_status).lower()
                    if internal and status_l in (
                        "closed",
                        "resolved",
                        "solved",
                        "complete",
                        "completed",
                        "6",
                        "5",
                    ):
                        if internal.status not in ("resolved", "closed"):
                            internal.status = (
                                "resolved" if status_l in ("resolved", "solved") else "closed"
                            )
                            if internal.status == "resolved" and not internal.resolved_at:
                                internal.resolved_at = _utcnow()
                            if internal.status == "closed" and not internal.closed_at:
                                internal.closed_at = _utcnow()
                    action = f"updated link {link.id} status={new_status}"
                elif link:
                    link.last_synced_at = _utcnow()
                    action = f"touched link {link.id}"
                else:
                    action = f"no local link for external ticket {ext_ticket_s}"

            event.status = "processed"
            event.action = action
            event.processed_at = _utcnow()
            conn.last_sync_at = _utcnow()
            conn.last_sync_status = "ok"
            conn.last_sync_error = None
            self.db.commit()
            self.db.refresh(event)
            return {
                "status": "processed",
                "action": action,
                "event_id": event.id,
                "duplicate": False,
            }
        except Exception as e:
            event.status = "error"
            event.error = str(e)
            event.processed_at = _utcnow()
            conn.last_sync_status = "error"
            conn.last_sync_error = str(e)
            self.db.commit()
            raise
