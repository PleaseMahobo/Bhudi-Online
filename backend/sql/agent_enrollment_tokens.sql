-- Production migration for reusable tenant-scoped agent enrollment tokens.
CREATE TABLE IF NOT EXISTS agent_enrollment_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NULL,
    used_at TIMESTAMPTZ NULL,
    agent_id UUID NULL REFERENCES agents(id) ON DELETE SET NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_enrollment_tokens_tenant_id
    ON agent_enrollment_tokens (tenant_id);

CREATE INDEX IF NOT EXISTS ix_agent_enrollment_tokens_token_hash
    ON agent_enrollment_tokens (token_hash);

CREATE INDEX IF NOT EXISTS ix_agent_enrollment_tokens_agent_id
    ON agent_enrollment_tokens (agent_id);
