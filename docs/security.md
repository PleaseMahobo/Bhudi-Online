# Security Engineering

## Purpose

This document explains the security engineering approach demonstrated by Bhudi Online. It intentionally excludes production secrets, credentials, private endpoints, customer information, and exploitable operational details.

## Security objectives

1. Confidentiality — protected data and credentials must not be unnecessarily exposed.
2. Integrity — unauthorized users must not alter protected resources.
3. Availability — critical services should remain resilient and observable.
4. Accountability — security-sensitive actions should be testable and traceable.
5. Least privilege — identities and services receive only the access required for their role.

## Authentication and authorization

Authentication establishes who the caller is. Authorization determines what that identity is allowed to do.

Unauthenticated → authenticated → identity established → role/tenant/resource authorization → permitted operation.

Tests should explicitly cover both positive and negative paths.

## MFA

MFA is treated as an additional authentication factor rather than a substitute for authorization. Validation should cover enrollment, verification, invalid or expired factors, recovery paths, session behaviour, and authorization after authentication.

## API security

API endpoints should enforce authorization at the server boundary rather than relying on frontend visibility. Security testing should include missing credentials, invalid credentials, expired sessions, insufficient privileges, cross-tenant/resource access attempts, malformed input, and replay or duplicate-request conditions where applicable.

## Identity reconciliation

Identity reconciliation is a controlled security operation:

candidate identity → exact-match verification → precondition validation → minimal authorized change → post-change validation → evidence.

Unconfirmed identities should remain unchanged rather than being automatically merged.

## Database security

Database access is protected through application authorization and appropriate database-level controls. Hiding a resource in the UI is not equivalent to protecting it.

## Remote-input security

Remote-control functionality requires a distinct security boundary because it can carry high-impact commands. The CI pipeline includes a focused regression test for the authenticated remote-input channel.

## CI/CD security

GitHub Actions provides repeatable validation including backend dependencies and pytest execution, focused security regression testing, frontend type checking/builds, agent validation, and Docker image construction/publication.

Secrets should be supplied through protected CI/runtime configuration rather than committed to source control.

## Security testing model

Identify asset → identify trust boundary → identify abuse case → create test → implement control → run regression test → review result.

## Framework alignment

The project can be reviewed against common OWASP application-security concerns and relevant MITRE ATT&CK techniques when investigating adversary behaviour. ATT&CK mappings should follow observed behaviour rather than being added merely for appearance.

## Responsible disclosure

This repository intentionally does not publish production credentials, tokens, private keys, customer data, or weaponized exploit material. Security findings should be reported responsibly and with enough information to reproduce the issue safely without exposing real users or production infrastructure.
