'use client';

import { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import BhudiLogo from '@/shared/components/BhudiLogo';
import { confirmPasswordReset } from '@/lib/auth-client';

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (!token) {
      setError('Invalid or missing reset token. Please request a new link.');
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(token, password);
      setSuccess(true);
      setTimeout(() => router.push('/login'), 2500);
    } catch (err: any) {
      setError(err?.message || 'Could not reset password. The link may have expired.');
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="space-y-6 text-center">
        <p className="rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          Invalid or missing reset link. Please request a new one.
        </p>
        <Link href="/forgot-password" className="text-sm text-indigo-400 hover:text-indigo-300">
          Request a new reset link
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="space-y-6 text-center">
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/40 px-4 py-4 text-sm text-emerald-300">
          Password updated successfully. Redirecting you to sign in…
        </div>
        <Link href="/login" className="text-sm text-indigo-400 hover:text-indigo-300">
          Go to Sign In now
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="text-xs font-medium text-slate-400">New password</label>
        <input
          type="password"
          placeholder="At least 12 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
          required
          minLength={12}
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-400">Confirm password</label>
        <input
          type="password"
          placeholder="Repeat new password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
          required
          minLength={12}
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
        {loading ? 'Updating…' : 'Set New Password'}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0F172A] p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900 p-10 shadow-xl">
        <div className="mb-10 flex flex-col items-center text-center">
          <BhudiLogo href="/" size="lg" variant="full" />
          <p className="mt-3 text-sm text-slate-400">Choose a new password</p>
        </div>
        <Suspense fallback={<p className="text-center text-slate-400">Loading…</p>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
