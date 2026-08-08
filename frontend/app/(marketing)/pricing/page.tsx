import Link from 'next/link';
import { Check } from 'lucide-react';

export const metadata = {
  title: 'Pricing — Bhudi',
  description: 'Simple plans for MSPs and enterprise IT teams.',
};

const PLANS = [
  {
    name: 'Starter',
    price: 'Contact us',
    blurb: 'For lean IT teams evaluating Bhudi on a focused estate.',
    features: ['Core RMM & inventory', 'Alert engine', 'Ticketing', 'Email support'],
    cta: 'Start Free Trial',
    href: '/trial',
    highlighted: false,
  },
  {
    name: 'Professional',
    price: 'Custom',
    blurb: 'Full operations platform for MSPs and mid-size enterprise IT.',
    features: [
      'Everything in Starter',
      'Bhudi AI assistant',
      'Print management',
      'Endpoint security posture',
      'Automation & scripts',
      'Priority support',
    ],
    cta: 'Book a Demo',
    href: '/contact',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    blurb: 'Scale, governance, and integration depth for complex environments.',
    features: [
      'Everything in Professional',
      'Advanced multi-tenant controls',
      'Custom integrations',
      'Dedicated success',
      'SSO & advanced audit',
    ],
    cta: 'Contact Sales',
    href: '/contact',
    highlighted: false,
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-semibold text-indigo-600">Pricing</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
          Plans that match how you operate
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Transparent packaging. We&apos;ll right-size seats, devices, and modules
          with you — no surprise add-on maze.
        </p>
      </div>

      <div className="mt-14 grid gap-6 lg:grid-cols-3">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`flex flex-col rounded-2xl border p-8 shadow-sm ${
              plan.highlighted
                ? 'border-indigo-300 bg-indigo-50/40 ring-2 ring-indigo-200'
                : 'border-slate-200 bg-white'
            }`}
          >
            <h2 className="text-lg font-semibold text-slate-900">{plan.name}</h2>
            <p className="mt-2 text-3xl font-bold tracking-tight text-[#0F172A]">{plan.price}</p>
            <p className="mt-2 text-sm text-slate-600">{plan.blurb}</p>
            <ul className="mt-6 flex-1 space-y-3">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-slate-700">
                  <Check size={16} className="mt-0.5 shrink-0 text-emerald-500" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href={plan.href}
              className={`mt-8 inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                plan.highlighted
                  ? 'bg-indigo-600 text-white hover:bg-indigo-500'
                  : 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50'
              }`}
            >
              {plan.cta}
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
