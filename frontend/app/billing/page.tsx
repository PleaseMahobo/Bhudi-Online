'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Check, CreditCard, Loader2, Shield } from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

type Plan = {
  code: string;
  name: string;
  description?: string;
  price_monthly?: number;
  price_cents?: number;
  features?: string[];
  popular?: boolean;
};

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
  return token
    ? { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

function BillingInner() {
  const search = useSearchParams();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const success = search.get('success') === '1';
  const canceled = search.get('canceled') === '1';

  const load = useCallback(async () => {
    setError('');
    try {
      const [pRes, sRes] = await Promise.all([
        fetch(API_BASE + '/api/v1/billing/plans', { headers: authHeaders() }),
        fetch(API_BASE + '/api/v1/billing/status', { headers: authHeaders() }),
      ]);
      const pJson = await pRes.json().catch(() => ({}));
      const sJson = await sRes.json().catch(() => ({}));
      setPlans(pJson.plans || []);
      setStatus(sJson);
    } catch (e: any) {
      setError(e?.message || 'Failed to load billing');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function startCheckout(planCode: string) {
    setBusy(planCode);
    setError('');
    try {
      const email =
        typeof window !== 'undefined'
          ? localStorage.getItem('user_email') || undefined
          : undefined;
      const res = await fetch(API_BASE + '/api/v1/billing/checkout', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          plan_code: planCode,
          email,
          success_url: window.location.origin + '/billing?success=1&plan=' + planCode,
          cancel_url: window.location.origin + '/billing?canceled=1',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 503) {
          setError(
            typeof data.detail === 'string'
              ? data.detail
              : 'Stripe not configured. Set STRIPE_SECRET_KEY on the API.'
          );
          return;
        }
        throw new Error(
          typeof data.detail === 'string' ? data.detail : res.statusText || 'Checkout failed'
        );
      }
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      setError('No checkout URL returned');
    } catch (e: any) {
      setError(e?.message || 'Checkout failed');
    } finally {
      setBusy(null);
    }
  }

  return (
    <ModuleShell title="Billing" subtitle="Subscribe with card or PayPal — linked to your Bhudi account">
      {success && (
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Payment received. Your subscription activates when Stripe confirms the webhook.
        </div>
      )}
      {canceled && (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Checkout canceled — no charge was made.
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
        <Shield size={16} className="text-indigo-600" />
        <span>
          Secure checkout via Stripe. Pay with <strong>credit/debit card</strong>
          {status?.paypal_via_stripe ? ' or PayPal' : ''}.
        </span>
        {status && (
          <span
            className={
              'ml-auto rounded-full px-2.5 py-0.5 text-xs font-medium ' +
              (status.stripe_configured
                ? 'bg-emerald-50 text-emerald-800'
                : 'bg-amber-50 text-amber-900')
            }
          >
            {status.mode || 'unconfigured'}
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.code}
            className={
              'relative flex flex-col rounded-2xl border bg-white p-6 shadow-sm ' +
              (plan.popular ? 'border-indigo-300 ring-2 ring-indigo-100' : 'border-slate-200')
            }
          >
            {plan.popular && (
              <span className="absolute -top-2.5 right-4 rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] font-semibold uppercase text-white">
                Popular
              </span>
            )}
            <h3 className="text-lg font-semibold text-slate-900">{plan.name}</h3>
            <p className="mt-1 text-sm text-slate-500">{plan.description}</p>
            <p className="mt-4 text-3xl font-bold text-slate-900">
              ${plan.price_monthly ?? Math.round((plan.price_cents || 0) / 100)}
              <span className="text-sm font-normal text-slate-500">/mo</span>
            </p>
            <ul className="mt-4 flex-1 space-y-2">
              {(plan.features || []).map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                  <Check size={14} className="mt-0.5 shrink-0 text-emerald-600" />
                  {f}
                </li>
              ))}
            </ul>
            <button
              type="button"
              disabled={busy === plan.code}
              onClick={() => startCheckout(plan.code)}
              className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {busy === plan.code ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <CreditCard size={16} />
              )}
              Pay with card / PayPal
            </button>
          </div>
        ))}
      </div>

      <p className="mt-6 text-center text-xs text-slate-500">
        New here?{' '}
        <Link href="/signup" className="text-indigo-600 hover:underline">
          Create an account
        </Link>{' '}
        first — billing uses your login email.
      </p>
    </ModuleShell>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-slate-500">Loading billing…</div>}>
      <BillingInner />
    </Suspense>
  );
}
