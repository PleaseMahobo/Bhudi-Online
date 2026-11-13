'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Sparkles } from 'lucide-react';
import { registerUser } from '@/lib/auth-client';

/**
 * Starter signup — create an account with profile details.
 * Agent download appears after payment. MFA is required later for Remote / Run command.
 */
export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [company, setCompany] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [accepted, setAccepted] = useState(false);

  async function onRegister(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!firstName.trim() || !lastName.trim()) {
      setError('Please enter your first and last name.');
      return;
    }
    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    if (!accepted) {
      setError('Accept the terms, including the refund, cancellation, and delivery policies, to create an account.');
      return;
    }
    setLoading(true);
    try {
      const result = await registerUser({
        email,
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        company: company.trim() || undefined,
      });
      if (result.requiresEmailVerification) {
        setSuccess('Account created. Check ' + email + ' for the verification link, then return here and sign in.');
        setPassword('');
        return;
      }
      if (typeof window !== 'undefined') {
        localStorage.setItem('bhudi_access_tier', 'starter');
        if (company.trim()) localStorage.setItem('bhudi_company', company.trim());
      }
      router.push('/dashboard?welcome=1');
    } catch (err: any) {
      setError(err?.message || 'Registration failed');
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
          <p className="mt-1 text-xs text-slate-500">
            This is the only sign-up page for Cyber Bastion and Bhudi. Payment happens here after you sign in.
          </p>
        </div>

        <form onSubmit={onRegister} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400">First name</label>
              <input
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Last name</label>
              <input
                required
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400">Company (optional)</label>
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Organisation name"
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
            />
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

          <div className="rounded-xl border border-slate-700/80 bg-slate-950/60 px-3 py-2.5 text-xs text-slate-400">
            After you subscribe, a Download agent button appears on your dashboard.
            Remote control and commands require multi-factor authentication.
          </div>

          <label className="flex items-start gap-2 text-xs leading-relaxed text-slate-400">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              className="mt-0.5"
              required
            />
            <span>
              I agree to the{' '}
              <Link href="/terms" className="text-indigo-400 hover:text-indigo-300">
                terms and conditions
              </Link>
              , including the{' '}
              <Link href="/terms#refunds" className="text-indigo-400 hover:text-indigo-300">
                refund
              </Link>
              ,{' '}
              <Link href="/terms#cancellation" className="text-indigo-400 hover:text-indigo-300">
                cancellation
              </Link>
              , and{' '}
              <Link href="/terms#delivery" className="text-indigo-400 hover:text-indigo-300">
                delivery
              </Link>{' '}
              policies. The same account is used on cyberbastion.co.za and bhudi.online.
            </span>
          </label>

          {error && (
            <p className="rounded-xl border border-red-500/40 bg-red-950/40 px-3 py-2 text-sm text-red-300">
              {error}
            </p>
          )}
          {success && (
            <p className="rounded-xl border border-emerald-500/40 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-300">
              {success}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

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
