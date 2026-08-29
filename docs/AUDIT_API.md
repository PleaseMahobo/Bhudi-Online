# Audit API

Base path: `/api/v1/audit`  
OpenAPI tag: **audit**  
Interactive docs: `/docs` (Swagger UI) or `/redoc`

All endpoints require a valid Bearer access token.

---

## Overview

The audit trail records privileged and application events in the `audit_trail` table.

| Source | How entries are written |
|--------|-------------------------|
| Client / portal | `POST /api/v1/audit/logs` |
| Platform admin actions | `app.services.audit_service.record_audit()` (server-side) |

List results include **both** sources.

---

## Endpoints

### `GET /api/v1/audit/logs`

List audit entries (newest first).

**Permission:** `audit.read`

| Query param | Type | Default | Description |
|-------------|------|---------|-------------|
| `limit` | int | `50` | Max rows (1–200) |
| `since` | datetime | — | ISO-8601 lower bound on `created_at` |
| `action` | string | — | Exact action key filter |
| `resource` | string | — | Exact resource filter |

**Example**

```http
GET /api/v1/audit/logs?limit=20&action=billing.admin.force_activate
Authorization: Bearer <token>
```

**200 response**

```json
{
  "items": [
    {
      "id": "a1b2c3d4-…",
      "tenant_id": "…",
      "user_id": "…",
      "action": "billing.admin.force_activate",
      "resource": "tenant:…",
      "details": {
        "actor_email": "security@bhudi.online",
        "plan_code": "enterprise",
        "prior_status": null,
        "new_status": "active",
        "new_device_limit": 1000000
      },
      "created_at": "2026-08-29T10:15:00Z"
    }
  ]
}
```

**Errors**

| Status | When |
|--------|------|
| 401 | Missing / invalid token |
| 403 | User lacks `audit.read` |
| 503 | Database unavailable |

---

### `POST /api/v1/audit/logs`

Record a client-originated audit event for the **current** user/tenant.

**Permission:** any authenticated user

**Body**

```json
{
  "action": "portal.settings.update",
  "resource": "settings:notifications",
  "details": { "field": "email_alerts", "value": true }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `action` | yes | Machine key (1–256 chars) |
| `resource` | no | Target identifier |
| `details` | no | Arbitrary JSON object |

**201 response**

```json
{
  "status": "recorded",
  "id": "a1b2c3d4-…"
}
```

`tenant_id` and `user_id` are always taken from the authenticated session (clients cannot spoof another actor).

---

## System-generated admin actions

These are written automatically by the backend (not via `POST /audit/logs`):

| Action key | Endpoint / trigger | Typical `resource` |
|------------|--------------------|--------------------|
| `billing.admin.inspect` | `GET /billing/admin/subscription` | `tenant:<uuid>` |
| `billing.admin.force_activate` | `POST /billing/admin/subscription/activate` | `tenant:<uuid>` |
| `billing.admin.seed_plans` | `POST /billing/admin/plans/seed` | `billing_plans` |
| `auth.platform_heal` | `POST /auth/platform-heal` | `user:<uuid>` |

Filter for admin activity:

```http
GET /api/v1/audit/logs?action=billing.admin.force_activate
GET /api/v1/audit/logs?action=auth.platform_heal
```

---

## Data model (`audit_trail`)

| Column | Type | Notes |
|--------|------|--------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID? | Tenant scope |
| `user_id` | UUID? | Acting user |
| `action` | text | Machine-readable key |
| `resource` | text | Target id / label |
| `details` | JSON | Structured context |
| `created_at` | timestamptz | Server default `now()` |

---

## Related code

| Path | Role |
|------|------|
| `backend/app/api/v1/endpoints/audit.py` | HTTP routes |
| `backend/app/schemas/audit.py` | Request / response models |
| `backend/app/models/audit_trail.py` | SQLAlchemy model |
| `backend/app/services/audit_service.py` | `record_audit()` helper for server-side writes |
