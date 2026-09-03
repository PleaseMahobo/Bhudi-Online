# Bhudi Tray Ticketing

This feature branch contains the isolated implementation plan for the Bhudi Windows system-tray companion and native endpoint ticketing.

## Scope

- Windows tray companion running in the interactive user session
- Log a Ticket workflow
- Secure ticket submission tied to enrolled agent/device and tenant identity
- Automatic machine context and diagnostics
- Ticket lifecycle support in the Bhudi backend/dashboard
- Installer and user-logon startup integration

## Security

Tenant and machine identity must be derived from authenticated agent credentials and server-side enrollment context. The tray UI must never be trusted to select another tenant.

PR #77 remains independent and focused on production enrollment-token promotion.
