'use client';

import BhudiLogo from '@/shared/components/BhudiLogo';
import { useState } from 'react';
import Link from 'next/link';
import { requestPasswordReset } from '@/lib/auth-client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMsg('');
    try {
      const res = await requestPasswordReset(email);
      setMsg(res.message || 'If an account exists for that email, reset instructions have been sent.');
    } catch (err: any) {
      setError(err?.message || 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0F172A] p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900 p-10 shadow-xl">
        <div className="mb-8 text-center">
          <BhudiLogo href="/" size="lg" variant="full" />
          <p className="mt-3 text-sm text-slate-400">Reset your password</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-slate-400">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-indigo-500"
              placeholder="you@company.com"
            />
          </div>
          {msg && <p className="text-sm text-emerald-300">{msg}</p>}
          {error && <p className="text-sm text-red-300">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? 'Sending…' : 'Send reset link'}
          </button>
        </form>
        <p className="mt-8 text-center text-xs text-slate-500">
          <Link href="/login" className="text-indigo-400">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
