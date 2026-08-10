'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Sparkles, ShieldCheck } from 'lucide-react';
import { loginUser, mfaSetup, mfaVerify, registerUser } from '@/lib/auth-client';

type Step = 'account' | 'mfa' | 'done';

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('account');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [secret, setSecret] = useState('');
  const [otpauth, setOtpauth] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onRegister(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    setLoading(true);
    try {
      await registerUser({
        email,
        password,
        first_name: firstName || undefined,
        last_name: lastName || undefined,
      });
      const tokens = await loginUser(email, password);
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', tokens.access_token);
        if (tokens.refresh_token) localStorage.setItem('refresh_token', tokens.refresh_token);
      }
      const mfa = await mfaSetup();
      setSecret(mfa.secret);
      setOtpauth(mfa.otpauth_uri);
      setStep('mfa');
    } catch (err: any) {
      setError(err?.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  async function onVerifyMfa(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await mfaVerify(mfaCode.trim());
      if (!res.enabled) {
        setError('Invalid code — try again.');
        return;
      }
      setStep('done');
    } catch (err: any) {
      setError(err?.message || 'MFA verification failed');
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
          <p className="mt-3 text-sm text-slate-400">Create your account</p>
        </div>

        {step === 'account' && (
          <form onSubmit={onRegister} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400">First name</label>
                <input
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400">Last name</label>
                <input
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400">Work email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Password (min 12 characters)</label>
              <input
                type="password"
                required
                minLength={12}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex items-start gap-2 rounded-xl border border-indigo-500/30 bg-indigo-950/40 px-3 py-2 text-xs text-indigo-200">
              <ShieldCheck size={16} className="mt-0.5 shrink-0" />
              <span>
                Multi-factor authentication (TOTP) is <strong>required</strong> after signup. You will
                enroll an authenticator app in the next step.
              </span>
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Creating account…' : 'Continue to MFA setup'}
            </button>
          </form>
        )}

        {step === 'mfa' && (
          <form onSubmit={onVerifyMfa} className="space-y-4">
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
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
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
              {loading ? 'Verifying…' : 'Enable MFA & finish'}
            </button>
          </form>
        )}

        {step === 'done' && (
          <div className="space-y-4 text-center">
            <ShieldCheck className="mx-auto text-emerald-400" size={40} />
            <p className="text-sm text-slate-300">Account ready. MFA is enabled.</p>
            <button
              type="button"
              onClick={() => router.push('/dashboard')}
              className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              Open dashboard
            </button>
          </div>
        )}

        <p className="mt-8 text-center text-xs text-slate-500">
          Already have an account?{' '}
          <Link href="/login" className="text-indigo-400 hover:text-indigo-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
