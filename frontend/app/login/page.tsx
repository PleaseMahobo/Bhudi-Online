'use client';

import BhudiLogo from '@/shared/components/BhudiLogo';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/shared/auth/AuthContext';
import { loginUser } from '@/lib/auth-client';

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [needMfa, setNeedMfa] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await loginUser(email, password, needMfa ? mfaCode : undefined);
      await auth.refreshUser();
      router.replace('/dashboard');
    } catch (err: any) {
      const msg = String(err?.message || '').trim();
      if (msg.includes('mfa_required')) {
        setNeedMfa(true);
        setError('Enter the 6-digit code from your authenticator app.');
      } else if (msg.includes('Invalid authenticator')) {
        setNeedMfa(true);
        setError('Invalid authenticator code. Try the current code from your app.');
      } else {
        setError(msg || 'Sign in failed. Check your email and password.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0F172A] p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900 p-10 shadow-xl">
        <div className="mb-10 flex flex-col items-center text-center">
          <BhudiLogo href="/" size="lg" variant="full" />
          <p className="mt-3 text-sm text-slate-400">Sign in to your operations workspace</p>
        </div>
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
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-400">Password</label>
              <Link href="/forgot-password" className="text-xs text-indigo-400 hover:text-indigo-300">
                Forgot password?
              </Link>
            </div>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
              required
            />
          </div>
          {needMfa && (
            <div className="space-y-2">
              <p className="rounded-xl border border-indigo-500/30 bg-indigo-950/40 px-3 py-2 text-center text-xs text-indigo-200">
                MFA is already enabled. Enter the current 6-digit code from your authenticator app. No
                new QR code is required.
              </p>
              <label className="text-xs font-medium text-slate-400">Authenticator code</label>
              <input
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                autoFocus
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-center font-mono text-lg tracking-widest text-white outline-none focus:border-indigo-500"
                placeholder="000000"
                required
              />
            </div>
          )}
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
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
        <p className="mt-8 text-center text-xs text-slate-500">
          New to Bhudi?{' '}
          <Link href="/signup" className="font-medium text-indigo-400 hover:text-indigo-300">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
