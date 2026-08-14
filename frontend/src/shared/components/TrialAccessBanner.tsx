'use client';

import Link from 'next/link';
import { Shield } from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';

/**
 * Shown when the signed-in user can browse but has not enabled MFA yet.
 * Privileged actions (remote, commands) remain locked until MFA is on.
 */
export default function TrialAccessBanner() {
  const { user } = useAuth();
  const role = (user as any)?.role || '';
  const mfaEnabled = Boolean((user as any)?.mfa_enabled ?? (user as any)?.mfaEnabled);

  // Hide when MFA is already on, or role is clearly full admin with MFA assumed
  if (!user || mfaEnabled) return null;
  if (role === 'admin' && mfaEnabled) return null;

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-500/30 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
      <div className="flex items-start gap-2">
        <Shield className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
        <div>
          <p className="font-medium">Trial access — view only for live actions</p>
          <p className="text-xs text-amber-200/80">
            You can explore the dashboard and device list. Remote control and command execution require
            multi-factor authentication.
          </p>
        </div>
      </div>
      <Link
        href="/mfa/setup"
        className="rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-900 hover:bg-amber-400"
      >
        Enable MFA
      </Link>
    </div>
  );
}
