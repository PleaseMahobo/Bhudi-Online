# Bhudi staging deployment

This environment is intentionally isolated from production.

## Isolation requirements

- Use a dedicated Railway staging service/environment.
- Use a dedicated PostgreSQL database; never point staging at the production database.
- Set `BHUDI_RUNTIME_STORE` to a staging-only persistent path/volume.
- Use staging-only JWT, SMTP, Stripe and other integration credentials.
- Do not copy production secrets into this environment.
- The real Bhudi agent must use the staging API URL only.

## Validated image

Deploy the exact image produced by the green `main` CI run. Prefer the immutable SHA tag or digest rather than `latest`.

```text
ghcr.io/pleasemahobo/bhudi-online-api:14dd3d62834186a4aad707986ccb0946a5ece3a5
```

## Required environment

```text
DATABASE_URL=<STAGING_POSTGRES_URL>
BHUDI_RUNTIME_STORE=<STAGING_RUNTIME_STORE>
JWT_SECRET_KEY=<STAGING_ONLY_SECRET>
REDIS_URL=<STAGING_REDIS_URL>
RABBITMQ_URL=<STAGING_RABBITMQ_URL>
FRONTEND_URL=<STAGING_FRONTEND_URL>
OTEL_ENVIRONMENT=staging
OTEL_SERVICE_NAME=bhudi-api-staging
```

Keep the runtime store separate even when other services use shared infrastructure.

## Gate

1. Deploy the immutable image.
2. Run migrations against the staging database only.
3. Verify `/api/v1/health`.
4. Verify the agent runtime API is reachable over HTTPS.
5. Start a real Bhudi agent configured for the staging API.
6. Verify enrollment and identity persistence.
7. Verify heartbeat and telemetry persistence.
8. Create and execute a technician command.
9. Verify command result persistence.
10. Verify dashboard device state, alert generation and ITSM synchronization.
11. Verify invalid agent credentials are rejected.

Do not mark staging green until the real installed agent completes the complete lifecycle.
