'use client';

import { useState } from 'react';
import Link from 'next/link';
import BhudiLogo from '@/shared/components/BhudiLogo';
import { requestPasswordReset } from '@/lib/auth-client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (err: any) {
      // Always show success message for security (don't reveal if email exists)
      setSent(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0F172A] p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900 p-10 shadow-xl">
        <div className="mb-10 flex flex-col items-center text-center">
          <BhudiLogo href="/" size="lg" variant="full" />
          <p className="mt-3 text-sm text-slate-400">Reset your password</p>
        </div>

        {sent ? (
          <div className="space-y-6 text-center">
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/40 px-4 py-4 text-sm text-emerald-300">
              If an account exists for that email, password reset instructions have been sent.
              Check your inbox (and spam folder).
            </div>
            <Link
              href="/login"
              className="inline-block text-sm font-medium text-indigo-400 hover:text-indigo-300"
            >
              ← Back to Sign In
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-xs font-medium text-slate-400">Email</label>
              <input
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
                required
              />
            </div>

            {error && (
              <p className="rounded-xl border border-red-500/40 bg-red-950/40 px-3 py-2 text-center text-sm text-red-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Sending…' : 'Send Reset Link'}
            </button>

            <p className="text-center text-xs text-slate-500">
              <Link href="/login" className="text-indigo-400 hover:text-indigo-300">
                ← Back to Sign In
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
