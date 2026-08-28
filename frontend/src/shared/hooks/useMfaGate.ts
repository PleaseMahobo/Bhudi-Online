'use client';

import { useAuth } from '@/shared/auth/AuthContext';

/**
 * Privileged actions (Remote desktop, Terminal, Run command) require MFA.
 * Signup itself does not require MFA — only these operations do.
 */
export function useMfaGate() {
  const { user, loading } = useAuth();
  const mfaEnabled = Boolean(user?.mfa_enabled);
  const ready = !loading;

  return {
    ready,
    mfaEnabled,
    user,
    /** True when we know MFA is required and missing */
    blocked: ready && !!user && !mfaEnabled,
    setupPath: '/mfa/setup' as const,
    message:
      'Enable multi-factor authentication before remote access or command execution.',
  };
}
