import Link from 'next/link';
import { Check } from 'lucide-react';
import { PageHero, CtaBand, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Pricing — Bhudi',
  description:
    'Starter, Professional, and Enterprise plans for individuals, organisations, and MSPs — aligned with the Bhudi portal.',
};

/** Portal-aligned plans (see backend DEFAULT_PLANS / BillingPlan seed). */
const PLANS = [
  {
    name: 'Starter',
    code: 'starter',
    price: '$49',
    period: 'per month',
    blurb: '1 managed endpoint — personal or single device. Install once, stay connected, get help when you need it.',
    features: [
      '1 managed device',
      'Native Windows agent (install once)',
      'Remote access & terminal',
      'Ticketing',
      'Email support',
      'Stays online after reboot',
    ],
    cta: 'Start Starter trial',
    href: '/signup?plan=starter',
    highlighted: false,
    accent: 'slate' as const,
  },
  {
    name: 'Professional',
    code: 'pro',
    price: '$149',
    period: 'per month',
    blurb: 'Up to 250 endpoints — organisations and MSPs. Org enroll, automation, and priority support.',
    features: [
      'Up to 250 devices',
      'Organisation enroll tokens',
      'Remote access & automation',
      'Ticketing & ITSM',
      'Priority support',
      'Device status & alerts',
    ],
    cta: 'Start Professional trial',
    href: '/signup?plan=pro',
    highlighted: true,
    accent: 'indigo' as const,
  },
  {
    name: 'Enterprise',
    code: 'enterprise',
    price: '$399',
    period: 'per month',
    blurb: 'Unlimited scale with dedicated support — SSO, compliance, white-label, and a custom SLA.',
    features: [
      'Unlimited devices',
      'SSO & compliance tools',
      'White-label options',
      'Dedicated CSM',
      'Custom SLA',
      'Full platform access',
    ],
    cta: 'Start Enterprise trial',
    href: '/signup?plan=enterprise',
    highlighted: false,
    accent: 'slate' as const,
  },
];

const FAQ = [
  {
    q: 'Do these match what I see in the portal?',
    a: 'Yes. Starter, Professional, and Enterprise are the same plan codes used for billing and entitlements in the Bhudi operations portal.',
  },
  {
    q: 'Can I start with one PC and grow later?',
    a: 'Yes. Start on Starter (1 device), then upgrade to Professional (250) or Enterprise (unlimited) as your estate grows.',
  },
  {
    q: 'Do I need to reinstall the agent when I change plans?',
    a: 'No. Install once. Entitlements update on the server; the agent keeps heartbeating and connecting.',
  },
  {
    q: 'Is the agent only for Windows?',
    a: 'The production native agent is optimised for Windows. Linux and macOS binaries are available for monitoring workloads.',
  },
  {
    q: 'Need a custom contract or MSP white-label?',
    a: 'Enterprise covers scale and dedicated support. For partner or volume pricing, contact us from the contact page.',
  },
];

export default function PricingPage() {
  return (
    <>
      <PageHero
        label="Pricing"
        title="Plans that match your portal"
        subtitle="Starter, Professional, and Enterprise — the same tiers you select inside Bhudi. Clear device limits, remote access, and support levels."
        primaryHref="/signup?plan=pro"
        primaryLabel="Start Professional trial"
        secondaryHref="/contact"
        secondaryLabel="Talk to sales"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <p className="mb-8 text-center text-sm text-slate-500">
          USD · cancel anytime · trial available · same plans as portal billing
        </p>
        <div className="grid gap-6 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <div
              key={plan.code}
              className={`flex flex-col rounded-2xl border p-8 shadow-sm ${
                plan.highlighted
                  ? 'border-indigo-300 bg-indigo-50/50 ring-2 ring-indigo-200'
                  : plan.code === 'enterprise'
                    ? 'border-slate-300 bg-slate-50/80'
                    : 'border-slate-200 bg-white'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-slate-900">{plan.name}</h2>
                {plan.highlighted ? (
                  <span className="rounded-full bg-indigo-600 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                    Popular
                  </span>
                ) : null}
                {plan.code === 'enterprise' ? (
                  <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                    Scale
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">{plan.price}</p>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{plan.period}</p>
              <p className="mt-3 text-sm text-slate-600">{plan.blurb}</p>
              <ul className="mt-6 flex-1 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-slate-700">
                    <Check
                      size={16}
                      className={`mt-0.5 shrink-0 ${
                        plan.highlighted ? 'text-indigo-600' : 'text-emerald-500'
                      }`}
                    />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href={plan.href}
                className={`mt-8 inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                  plan.highlighted
                    ? 'bg-indigo-600 text-white hover:bg-indigo-500'
                    : plan.code === 'enterprise'
                      ? 'bg-slate-900 text-white hover:bg-slate-800'
                      : 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-slate-100 bg-slate-50">
        <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
          <SectionLabel>FAQ</SectionLabel>
          <h2 className="mt-2 text-2xl font-bold text-[#0F172A]">Common questions</h2>
          <dl className="mt-8 space-y-6">
            {FAQ.map((item) => (
              <div key={item.q} className="rounded-2xl border border-slate-200 bg-white p-5">
                <dt className="font-semibold text-slate-900">{item.q}</dt>
                <dd className="mt-2 text-sm leading-relaxed text-slate-600">{item.a}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <CtaBand
        title="Same plans in the portal and on the website"
        body="Pick Starter, Professional, or Enterprise — device limits and features match your Bhudi entitlement."
        primaryHref="/signup?plan=pro"
        primaryLabel="Create account"
        secondaryHref="/agents"
        secondaryLabel="Download agent"
      />
    </>
  );
}
