'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MailCheck, ShieldCheck, Sparkles } from 'lucide-react';
import { mfaVerify } from '@/lib/auth-client';

export default function MfaSetupPage() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [done, setDone] = useState(false);
  const [alreadyEnabled, setAlreadyEnabled] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/auth/me', { credentials: 'include', cache: 'no-store' });
        const data = await res.json().catch(() => ({}));
        if (data?.mfa_enabled || data?.user?.mfa_enabled) {
          setAlreadyEnabled(true);
          setDone(true);
        }
      } catch {
        /* ignore */
      }
    })();
  }, []);

  async function startSetup(forceNew = false) {
    setError('');
    setInfo('');
    setLoading(true);
    try {
      const path = forceNew ? '/api/auth/mfa/setup?force_new=1' : '/api/auth/mfa/setup';
      const res = await fetch(path, {
        method: 'POST',
        credentials: 'include',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: '{}',
      });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof result?.detail === 'string' ? result.detail : result?.message || 'Could not start MFA setup');
      }
      if (result.already_enabled) {
        setAlreadyEnabled(true);
        setDone(true);
        setInfo(result.message || 'MFA is already enabled.');
        return;
      }
      if (!result.email_sent) {
        setError('We could not send the MFA setup email. Please try again.');
        return;
      }
      setStarted(true);
      setInfo(result.message || 'Check your email for the QR code.');
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
        setError('Invalid code — use the current code from the authenticator entry you scanned.');
        return;
      }
      if (typeof window !== 'undefined') {
        localStorage.setItem('bhudi_access_tier', 'secured');
        localStorage.setItem('bhudi_mfa_enabled', '1');
      }
      setDone(true);
      setAlreadyEnabled(true);
      // Re-enter the authenticated dashboard so AuthContext re-fetches /api/auth/me.
      // This removes the MFA banner from the live session instead of relying on localStorage.
      window.location.assign('/dashboard');
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
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600"><Sparkles size={18} /></span>
            Bhudi
          </Link>
          <p className="mt-3 text-sm text-slate-400">Secure your account</p>
          <p className="mt-1 text-xs text-slate-500">Scan the QR once. After that, login only needs the 6-digit authenticator code.</p>
        </div>

        {done || alreadyEnabled ? (
          <div className="space-y-4 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-400"><ShieldCheck size={28} /></div>
            <p className="text-sm text-slate-300">MFA is enabled. Future logins only need the 6-digit code from your authenticator — Bhudi will not keep emailing new QR codes.</p>
            {info ? <p className="text-xs text-slate-500">{info}</p> : null}
            <Link href="/dashboard" className="inline-flex w-full items-center justify-center rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500">Continue to dashboard</Link>
            <Link href="/billing" className="block text-center text-xs text-slate-500 hover:text-slate-300">Manage subscription</Link>
          </div>
        ) : !started ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 text-left text-xs leading-5 text-slate-400">
              <p className="font-medium text-slate-200">How MFA works</p>
              <ol className="mt-2 list-decimal space-y-1 pl-4">
                <li>We email you one QR code.</li><li>You scan it once in your authenticator app.</li><li>You enter the 6-digit code here to finish setup.</li><li>Every later login: password + that same 6-digit code only.</li>
              </ol>
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            {info && <p className="text-sm text-emerald-300">{info}</p>}
            <button type="button" disabled={loading} onClick={() => void startSetup(false)} className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">{loading ? 'Sending…' : 'Email me the QR code'}</button>
            <p className="text-center text-xs text-slate-500">Already scanned a QR before?{' '}<button type="button" className="text-indigo-400 hover:text-indigo-300" onClick={() => setStarted(true)}>Enter your 6-digit code</button></p>
            <Link href="/billing" className="block text-center text-xs text-slate-500 hover:text-slate-300">Complete payment first</Link>
            <Link href="/dashboard" className="block text-center text-xs text-slate-600 hover:text-slate-400">Back to trial dashboard</Link>
          </div>
        ) : (
          <form onSubmit={onVerify} className="space-y-4">
            <div className="rounded-xl border border-emerald-900/60 bg-emerald-950/30 p-4">
              <p className="flex items-center gap-2 text-sm font-medium text-emerald-300"><MailCheck size={16} /> Check your email (or use an existing scan)</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">Use the <strong className="text-slate-300">same</strong> authenticator entry. Do not keep adding new Bhudi accounts for every email.</p>
            </div>
            <div>
              <label className="text-xs text-slate-400">6-digit code</label>
              <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" maxLength={6} required className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-center font-mono text-lg tracking-widest text-white outline-none focus:border-indigo-500" />
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            {info && <p className="text-sm text-emerald-300">{info}</p>}
            <button type="submit" disabled={loading || code.length !== 6} className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">{loading ? 'Verifying…' : 'Enable MFA'}</button>
            <button type="button" disabled={loading} onClick={() => void startSetup(false)} className="w-full rounded-xl border border-slate-700 py-3 text-sm font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-50">Resend same QR by email</button>
            <button type="button" disabled={loading} onClick={() => { if (confirm('This creates a NEW secret. Delete all old Bhudi entries in your authenticator first, then scan the new QR.')) void startSetup(true); }} className="w-full text-xs text-slate-500 hover:text-amber-400">Reset MFA (new QR — only if lost access)</button>
          </form>
        )}
      </div>
    </div>
  );
}
