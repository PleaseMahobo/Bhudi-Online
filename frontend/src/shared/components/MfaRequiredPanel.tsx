'use client';

import Link from 'next/link';
import { ShieldAlert } from 'lucide-react';

type Props = {
  title?: string;
  className?: string;
  compact?: boolean;
};

/**
 * Clear CTA when Remote / Run command is blocked until MFA is set up.
 */
export default function MfaRequiredPanel({
  title = 'MFA required',
  className = '',
  compact = false,
}: Props) {
  if (compact) {
    return (
      <div
        className={
          'flex flex-wrap items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950 ' +
          className
        }
      >
        <ShieldAlert size={14} className="shrink-0 text-amber-700" />
        <span className="flex-1">Enable MFA to use Remote and Run command.</span>
        <Link
          href="/mfa/setup"
          className="rounded-lg bg-indigo-600 px-2.5 py-1 font-semibold text-white hover:bg-amber-500"
        >
          Set up MFA
        </Link>
      </div>
    );
  }

  return (
    <div
      className={
        'rounded-2xl border border-amber-200 bg-amber-50 px-5 py-5 text-amber-950 shadow-sm ' +
        className
      }
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-xl bg-amber-100 p-2">
          <ShieldAlert size={20} className="text-amber-700" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-amber-950">{title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-amber-900/90">
            Remote desktop, terminal, and command execution are locked until multi-factor
            authentication is enabled on your account. This protects device control actions.
          </p>
          <Link
            href="/mfa/setup"
            className="mt-4 inline-flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            Set up MFA
          </Link>
        </div>
      </div>
    </div>
  );
}
