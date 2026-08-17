'use client';

import Link from 'next/link';
import { CreditCard, Shield } from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';

/** Trial users: limited until payment + MFA. Hidden once MFA is enabled. */
export default function TrialAccessBanner() {
  const { user } = useAuth();
  const mfaEnabled = Boolean((user as any)?.mfa_enabled ?? (user as any)?.mfaEnabled);

  if (!user || mfaEnabled) return null;

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-500/30 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
      <div className="flex items-start gap-2">
        <Shield className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
        <div>
          <p className="font-medium">Trial workspace — limited access</p>
          <p className="text-xs text-amber-200/80">
            Browse overview pages only. Unlock full operations: paywall first, then enable MFA (one QR
            scan). After that, every login uses your authenticator code only — no repeated QR emails.
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Link
          href="/billing"
          className="inline-flex items-center gap-1 rounded-xl bg-indigo-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-400"
        >
          <CreditCard size={12} /> Go to paywall
        </Link>
        <Link
          href="/mfa/setup"
          className="rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-900 hover:bg-amber-400"
        >
          Enable MFA
        </Link>
      </div>
    </div>
  );
}
