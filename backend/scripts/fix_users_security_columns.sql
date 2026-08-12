-- Run against the Railway Postgres database used by Bhudi RMM.
-- Safe to re-run: only adds missing columns.

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_history JSONB NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS passkeys JSONB NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider VARCHAR(64) NULL;
