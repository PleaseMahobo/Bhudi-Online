# Phase 14A — Supabase Identity Bridge

Authentication boundary:

Supabase Auth → Bhudi identity mapping → existing tenant/RBAC authorization → existing PostgreSQL application.

## Required portal environment

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Validation

The backend bridge verifies the Supabase access token, maps the Supabase identity to the existing Bhudi user, rejects unknown/inactive users, and preserves the existing tenant and RBAC model.

The portal exchanges the Supabase session access token for a short-lived HttpOnly `access_token` cookie so existing Bhudi API routes continue to operate without browser token storage.

The existing custom password/refresh endpoints are retained during Phase 14A for rollback and are not removed by this change.
