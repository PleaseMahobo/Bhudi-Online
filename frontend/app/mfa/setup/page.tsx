'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { MailCheck, ShieldCheck, Sparkles } from 'lucide-react';
import { mfaSetup, mfaVerify } from '@/lib/auth-client';

/**
 * Standard Bhudi MFA enrollment: the provisioning QR code is delivered by
 * email and is never exposed as a raw secret in the browser UI.
 */
export default function MfaSetupPage() {
  const router = useRouter();
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [done, setDone] = useState(false);

  async function startSetup() {
    setError('');
    setLoading(true);
    try {
      const result = await mfaSetup();
      if (!result.email_sent) {
        setError('We could not send the MFA setup email. Please try again.');
        return;
      }
      setStarted(true);
    } catch (err: any) {
      setError(err?.message || 'Could not send the MFA setup email');
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
            <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 text-center">
              <MailCheck className="mx-auto mb-3 text-indigo-400" size={32} />
              <p className="text-sm font-medium text-white">We'll email your authenticator QR code</p>
              <p className="mt-2 text-xs leading-5 text-slate-400">
                The QR code will be sent to your registered Bhudi email address. We never display your authenticator secret on this page.
              </p>
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            <button
              type="button"
              disabled={loading}
              onClick={() => void startSetup()}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Sending QR code…' : 'Email me the QR code'}
            </button>
            <Link href="/dashboard" className="block text-center text-xs text-slate-500 hover:text-slate-300">
              Continue browsing without MFA
            </Link>
          </div>
        ) : (
          <form onSubmit={onVerify} className="space-y-4">
            <div className="rounded-xl border border-emerald-900/60 bg-emerald-950/30 p-4">
              <p className="text-sm font-medium text-emerald-300">Check your email</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">
                We sent your Bhudi MFA QR code by email. Scan it with Google Authenticator, Microsoft Authenticator, Authy, 1Password, or another compatible authenticator app.
              </p>
            </div>
            <div>
              <label className="text-xs text-slate-400">6-digit code</label>
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-center font-mono text-lg tracking-widest text-white outline-none focus:border-indigo-500"
              />
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Verifying…' : 'Enable MFA'}
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => void startSetup()}
              className="w-full rounded-xl border border-slate-700 py-3 text-sm font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-50"
            >
              Send a new QR code
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
