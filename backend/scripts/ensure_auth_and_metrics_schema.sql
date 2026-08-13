-- Bhudi: auth columns + metrics table/indexes
-- Run in Supabase SQL Editor (public schema)

-- ---------- users (register / login / MFA) ----------
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
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_users_email_lower ON public.users (lower(email));
CREATE INDEX IF NOT EXISTS idx_users_tenant ON public.users (tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON public.users (active);

-- ---------- device_metrics (graphs / Grafana) ----------
CREATE TABLE IF NOT EXISTS public.device_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NULL,
    cpu_usage NUMERIC NULL,
    ram_usage NUMERIC NULL,
    disk_usage NUMERIC NULL,
    recorded_at TIMESTAMPTZ DEFAULT now(),
    tenant_id UUID NULL
);

CREATE INDEX IF NOT EXISTS idx_device_metrics_device_recorded
    ON public.device_metrics (device_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_device_metrics_recorded
    ON public.device_metrics (recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_device_metrics_tenant_recorded
    ON public.device_metrics (tenant_id, recorded_at DESC)
    WHERE tenant_id IS NOT NULL;

-- Optional BRIN for large time-series scans
CREATE INDEX IF NOT EXISTS idx_device_metrics_recorded_brin
    ON public.device_metrics USING BRIN (recorded_at);

-- ---------- devices snapshot used by metrics upsert ----------
CREATE TABLE IF NOT EXISTS public.devices (
    id UUID PRIMARY KEY,
    hostname TEXT NULL,
    ip TEXT NULL,
    status TEXT NULL,
    cpu INTEGER NULL,
    ram INTEGER NULL,
    disk INTEGER NULL,
    last_seen TIMESTAMPTZ NULL,
    agent_version TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON public.devices (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_devices_status ON public.devices (status);
