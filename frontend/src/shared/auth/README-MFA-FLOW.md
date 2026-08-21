# Production login MFA flow

For accounts with MFA enabled, the application session is not established after password authentication alone.

Required sequence:

1. Login page accepts email and password.
2. Supabase validates the password.
3. Bhudi backend `/api/auth/login` checks whether MFA is enabled.
4. If MFA is enabled and no code is supplied, login remains on the login page and requests the 6-digit authenticator code.
5. The backend verifies the code.
6. Only after successful verification are the Bhudi HttpOnly application cookies issued.
7. `/api/auth/me` resolves the authenticated identity and tenant.
8. Dashboard access is allowed.

The dashboard must not promote a Supabase-only client session into an application session, and the dashboard MFA banner is intentionally removed. MFA setup remains a separate enrollment/reset operation rather than a normal-login step.
