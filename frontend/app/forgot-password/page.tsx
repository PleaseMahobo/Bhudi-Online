'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Sparkles } from 'lucide-react';
import { requestPasswordReset } from '@/lib/auth-client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState('');
  const [debugPath, setDebugPath] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMsg('');
    setDebugPath('');
    try {
      const res = await requestPasswordReset(email);
      setMsg(res.message || 'Check your email for reset instructions.');
      if (res.debug_reset_path) setDebugPath(res.debug_reset_path);
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
          <Link href="/" className="inline-flex items-center gap-2 font-semibold text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600">
              <Sparkles size={18} />
            </span>
            Bhudi
          </Link>
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
            />
          </div>
          {msg && <p className="text-sm text-emerald-300">{msg}</p>}
          {debugPath && (
            <p className="text-xs text-amber-200">
              Dev reset link:{' '}
              <Link href={debugPath} className="underline">
                {debugPath}
              </Link>
            </p>
          )}
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
