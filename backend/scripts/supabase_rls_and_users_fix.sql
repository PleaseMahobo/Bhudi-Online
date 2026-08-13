-- =============================================================================
-- Bhudi RMM — Supabase: fix public.users columns + enable Row Level Security
-- =============================================================================
-- HOW TO RUN
--   1. Supabase Dashboard → SQL Editor → New query
--   2. Paste this entire file → Run
--
-- ARCHITECTURE
--   - Railway FastAPI uses DATABASE_URL (postgres / service_role).
--     Those roles BYPASS RLS, so the API keeps working.
--   - anon / authenticated (browser, Supabase JS client) ARE subject to RLS.
--   - Default: no public client access to app tables (API-only backend).
--   - Optional tenant policies use JWT claim app_tenant_id if you set it later.
--
-- Do NOT run ALTER on auth.users (Supabase Auth). Only public.*
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0) Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- 1) Ensure public.users has columns expected by the FastAPI User model
--    (fixes: password_history does not exist)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF to_regclass('public.users') IS NULL THEN
    RAISE NOTICE 'public.users does not exist — create app tables/migrations first';
  END IF;
END $$;

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_history JSONB NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255) NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS passkeys JSONB NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS sso_provider VARCHAR(64) NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS tenant_id UUID NULL;

-- Unlock common admin emails after failed attempts
UPDATE public.users
SET failed_login_attempts = 0,
    locked_until = NULL,
    active = true
WHERE email IN (
  'admin@bhudi.online',
  'security@bhudi.online',
  'admin@bhudi.com'
);

-- ---------------------------------------------------------------------------
-- 2) Helpers for optional JWT-based tenant isolation (Supabase Auth clients)
--    FastAPI does not need these; they only affect roles subject to RLS.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.bhudi_jwt_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(
    COALESCE(
      auth.jwt() ->> 'app_tenant_id',
      auth.jwt() -> 'app_metadata' ->> 'tenant_id',
      auth.jwt() -> 'user_metadata' ->> 'tenant_id'
    ),
    ''
  )::uuid;
$$;

CREATE OR REPLACE FUNCTION public.bhudi_is_service()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(auth.role() IN ('service_role', 'postgres'), false);
$$;

-- ---------------------------------------------------------------------------
-- 3) Enable RLS on core public tables (skip if table missing)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'users',
    'tenants',
    'devices',
    'agents',
    'commands',
    'alerts',
    'alert_rules',
    'incidents',
    'refresh_tokens',
    'password_reset_tokens',
    'profiles',
    'roles',
    'permissions',
    'user_roles',
    'role_permissions',
    'audit_logs',
    'device_events',
    'device_heartbeats',
    'device_metrics',
    'notifications',
    'organizations',
    'msp_organizations'
  ];
BEGIN
  FOREACH t IN ARRAY tables
  LOOP
    IF to_regclass('public.' || t) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
      EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', t);
      RAISE NOTICE 'RLS enabled on public.%', t;
    END IF;
  END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- 4) Drop old Bhudi policies (idempotent re-run)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT schemaname, tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND policyname LIKE 'bhudi_%'
  LOOP
    EXECUTE format(
      'DROP POLICY IF EXISTS %I ON %I.%I',
      r.policyname, r.schemaname, r.tablename
    );
  END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- 5) Core policies
--    Pattern:
--      - service_role / postgres: full access (API)
--      - authenticated: optional self / tenant scoped where columns exist
--      - anon: no access (no policies = deny when RLS on)
-- ---------------------------------------------------------------------------

-- users
DO $$
BEGIN
  IF to_regclass('public.users') IS NULL THEN
    RETURN;
  END IF;

  CREATE POLICY bhudi_users_service_all
    ON public.users
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

  -- Authenticated users can read/update only their own row if id matches auth.uid()
  -- (only useful if you later link Supabase Auth users to public.users.id)
  CREATE POLICY bhudi_users_self_select
    ON public.users
    FOR SELECT
    TO authenticated
    USING (
      id::text = COALESCE(auth.uid()::text, '')
      OR tenant_id IS NOT DISTINCT FROM public.bhudi_jwt_tenant_id()
    );

  CREATE POLICY bhudi_users_self_update
    ON public.users
    FOR UPDATE
    TO authenticated
    USING (id::text = COALESCE(auth.uid()::text, ''))
    WITH CHECK (id::text = COALESCE(auth.uid()::text, ''));
END $$;

-- tenants
DO $$
BEGIN
  IF to_regclass('public.tenants') IS NULL THEN
    RETURN;
  END IF;

  CREATE POLICY bhudi_tenants_service_all
    ON public.tenants
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

  CREATE POLICY bhudi_tenants_member_select
    ON public.tenants
    FOR SELECT
    TO authenticated
    USING (id IS NOT DISTINCT FROM public.bhudi_jwt_tenant_id());
END $$;

-- devices (tenant scoped when tenant_id present)
DO $$
BEGIN
  IF to_regclass('public.devices') IS NULL THEN
    RETURN;
  END IF;

  CREATE POLICY bhudi_devices_service_all
    ON public.devices
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'devices' AND column_name = 'tenant_id'
  ) THEN
    CREATE POLICY bhudi_devices_tenant_select
      ON public.devices
      FOR SELECT
      TO authenticated
      USING (tenant_id IS NOT DISTINCT FROM public.bhudi_jwt_tenant_id());

    CREATE POLICY bhudi_devices_tenant_write
      ON public.devices
      FOR ALL
      TO authenticated
      USING (tenant_id IS NOT DISTINCT FROM public.bhudi_jwt_tenant_id())
      WITH CHECK (tenant_id IS NOT DISTINCT FROM public.bhudi_jwt_tenant_id());
  END IF;
END $$;

-- Generic service_role full access for remaining known tables
DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'agents',
    'commands',
    'alerts',
    'alert_rules',
    'incidents',
    'refresh_tokens',
    'password_reset_tokens',
    'profiles',
    'roles',
    'permissions',
    'user_roles',
    'role_permissions',
    'audit_logs',
    'device_events',
    'device_heartbeats',
    'device_metrics',
    'notifications',
    'organizations',
    'msp_organizations'
  ];
BEGIN
  FOREACH t IN ARRAY tables
  LOOP
    IF to_regclass('public.' || t) IS NOT NULL THEN
      EXECUTE format(
        'CREATE POLICY bhudi_%s_service_all ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)',
        t, t
      );
    END IF;
  END LOOP;
END $$;

-- Tenant-scoped SELECT for tables that have tenant_id (authenticated only)
DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'agents',
    'commands',
    'alerts',
    'incidents',
    'device_events',
    'device_heartbeats',
    'device_metrics',
    'notifications'
  ];
BEGIN
  FOREACH t IN ARRAY tables
  LOOP
    IF to_regclass('public.' || t) IS NOT NULL
       AND EXISTS (
         SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = t AND column_name = 'tenant_id'
       )
    THEN
      EXECUTE format(
        'CREATE POLICY bhudi_%s_tenant_select ON public.%I FOR SELECT TO authenticated USING (tenant_id IS NOT DISTINCT FROM public.bhudi_jwt_tenant_id())',
        t, t
      );
    END IF;
  END LOOP;
END $$;

-- refresh_tokens / password_reset_tokens: no client access (service only)
-- (already covered by service_role policy; no authenticated policies on purpose)

-- ---------------------------------------------------------------------------
-- 6) Verification
-- ---------------------------------------------------------------------------
SELECT
  c.relname AS table_name,
  c.relrowsecurity AS rls_enabled,
  c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relname IN (
    'users','tenants','devices','agents','commands','alerts','refresh_tokens'
  )
ORDER BY 1;

SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public' AND policyname LIKE 'bhudi_%'
ORDER BY tablename, policyname;

SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'users'
  AND column_name IN (
    'password_history',
    'failed_login_attempts',
    'password_hash',
    'locked_until',
    'mfa_enabled'
  )
ORDER BY 1;
