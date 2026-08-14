'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ShieldCheck, Sparkles } from 'lucide-react';
import { mfaSetup, mfaVerify } from '@/lib/auth-client';

/**
 * MFA is configured here — after trial signup, when the user needs privileged access.
 */
export default function MfaSetupPage() {
  const router = useRouter();
  const [secret, setSecret] = useState('');
  const [otpauth, setOtpauth] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [done, setDone] = useState(false);

  async function startSetup() {
    setError('');
    setLoading(true);
    try {
      const mfa = await mfaSetup();
      setSecret(mfa.secret);
      setOtpauth(mfa.otpauth_uri);
      setStarted(true);
    } catch (err: any) {
      setError(err?.message || 'Could not start MFA setup');
    } finally {
      setLoading(false);
    }
  }

  async function onVerify(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await mfaVerify(code.trim());
      if (!res.enabled) {
        setError('Invalid code — try again.');
        return;
      }
      if (typeof window !== 'undefined') {
        localStorage.setItem('bhudi_access_tier', 'secured');
      }
      setDone(true);
    } catch (err: any) {
      setError(err?.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0F172A] p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900 p-10 shadow-xl">
        <div className="mb-8 text-center">
          <Link href="/dashboard" className="inline-flex items-center gap-2 font-semibold text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600">
              <Sparkles size={18} />
            </span>
            Bhudi
          </Link>
          <p className="mt-3 text-sm text-slate-400">Secure your account</p>
          <p className="mt-1 text-xs text-slate-500">
            Multi-factor authentication is required before remote access and command execution.
          </p>
        </div>

        {done ? (
          <div className="space-y-4 text-center">
            <ShieldCheck className="mx-auto text-emerald-400" size={40} />
            <p className="text-sm text-slate-300">MFA enabled. Privileged actions are unlocked.</p>
            <button
              type="button"
              onClick={() => router.push('/dashboard')}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              Back to dashboard
            </button>
          </div>
        ) : !started ? (
          <div className="space-y-4">
            {error && <p className="text-sm text-red-300">{error}</p>}
            <button
              type="button"
              disabled={loading}
              onClick={() => void startSetup()}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Preparing…' : 'Set up authenticator'}
            </button>
            <Link href="/dashboard" className="block text-center text-xs text-slate-500 hover:text-slate-300">
              Continue browsing without MFA
            </Link>
          </div>
        ) : (
          <form onSubmit={onVerify} className="space-y-4">
            <p className="text-sm text-slate-300">
              Add Bhudi to Google Authenticator, Authy, or 1Password using the secret below.
            </p>
            <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
              <p className="text-[11px] text-slate-500">Secret</p>
              <p className="break-all font-mono text-xs text-emerald-300">{secret}</p>
              <p className="mt-2 text-[11px] text-slate-500">otpauth URI</p>
              <p className="break-all font-mono text-[10px] text-slate-400">{otpauth}</p>
            </div>
            <div>
              <label className="text-xs text-slate-400">6-digit code</label>
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                inputMode="numeric"
                maxLength={8}
                required
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-center font-mono text-lg tracking-widest text-white outline-none focus:border-indigo-500"
              />
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Verifying…' : 'Enable MFA'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
