'use client';

import Link from 'next/link';
import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';

const PERKS = [
  'Full module access during trial',
  'Sample estate to explore AI & alerts',
  'No credit card required to start',
  'Guided onboarding available',
];

export default function TrialPage() {
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSent(true);
    }, 700);
  };

  return (
    <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:items-start">
      <div>
        <p className="text-sm font-semibold text-indigo-600">Start Free Trial</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
          Try Bhudi on your terms
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Spin up a workspace and experience Monitor · Manage · Secure with Bhudi AI
          in the flow of work.
        </p>
        <ul className="mt-8 space-y-3">
          {PERKS.map((p) => (
            <li key={p} className="flex items-center gap-2 text-sm text-slate-700">
              <CheckCircle2 size={18} className="text-emerald-500" />
              {p}
            </li>
          ))}
        </ul>
        <p className="mt-8 text-sm text-slate-500">
          Already have an account?{' '}
          <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Login
          </Link>
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        {sent ? (
          <div className="text-center">
            <p className="text-lg font-semibold text-slate-900">You&apos;re on the list</p>
            <p className="mt-2 text-sm text-slate-600">
              We&apos;ll email trial access instructions shortly. You can also{' '}
              <Link href="/login" className="font-medium text-indigo-600">
                sign in
              </Link>{' '}
              if your workspace is already provisioned.
            </p>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-600">Full name</label>
              <input
                required
                className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">Work email</label>
              <input
                required
                type="email"
                className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">Company</label>
              <input
                required
                className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">Approx. endpoints</label>
              <select className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
                <option>1 – 100</option>
                <option>100 – 1,000</option>
                <option>1,000 – 5,000</option>
                <option>5,000+</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
            >
              {loading ? 'Submitting…' : 'Request trial access'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
