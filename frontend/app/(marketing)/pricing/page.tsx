import Link from 'next/link';
import { Check } from 'lucide-react';
import { PageHero, CtaBand, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Pricing — Bhudi',
  description: 'Indicative Bhudi packaging for pilots through multi-tenant MSP production.',
};

const PLANS = [
  {
    name: 'Starter',
    price: '$3',
    period: 'per device / month',
    blurb: 'Pilot remote access and core RMM on a focused device set.',
    features: [
      'Up to 50 devices (trial soft cap)',
      'Native agents (Windows / Linux / macOS)',
      'Remote desktop & terminal',
      'Device inventory & heartbeats',
      'Email support',
    ],
    cta: 'Start trial',
    href: '/trial',
    highlighted: false,
  },
  {
    name: 'Professional',
    price: '$6',
    period: 'per device / month',
    blurb: 'Full operations shell for MSPs and mid-size IT teams.',
    features: [
      'Everything in Starter',
      'Print management module',
      'Ticketing & ITSM views',
      'Automation & scripts',
      'Bhudi AI assistant',
      'Priority support',
    ],
    cta: 'Talk to sales',
    href: '/contact',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: 'volume & modules',
    blurb: 'Governance, SSO, and integration depth for complex estates.',
    features: [
      'Everything in Professional',
      'Advanced multi-tenant controls',
      'SSO / SAML',
      'Custom integrations',
      'Dedicated success',
      'Deployment assistance',
    ],
    cta: 'Contact sales',
    href: '/contact',
    highlighted: false,
  },
];

const FAQ = [
  {
    q: 'Are these final list prices?',
    a: 'Figures are indicative packaging for planning. Commercial agreements are quoted to your device count, modules, and support tier.',
  },
  {
    q: 'Is there a free trial?',
    a: 'Yes. Start from the trial page, deploy agents to a pilot group, and evaluate remote access before committing.',
  },
  {
    q: 'Do endpoints need Python?',
    a: 'No. Bhudi ships a native static agent for Windows, Linux, and macOS.',
  },
  {
    q: 'Minimum commitment?',
    a: 'Trials are month-to-month for evaluation. Production terms are agreed during sales onboarding.',
  },
];

export default function PricingPage() {
  return (
    <>
      <PageHero
        label="Pricing"
        title="Simple per-device packaging"
        subtitle="Indicative monthly pricing so you can plan a pilot. We right-size seats, modules, and support when you are ready to go live."
        primaryHref="/trial"
        primaryLabel="Start free trial"
        secondaryHref="/contact"
        secondaryLabel="Get a quote"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <p className="mb-8 text-center text-sm text-slate-500">
          Prices shown in USD · billed monthly · volume discounts available
        </p>
        <div className="grid gap-6 lg:grid-cols-3">
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
              <p className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">{plan.price}</p>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                {plan.period}
              </p>
              <p className="mt-3 text-sm text-slate-600">{plan.blurb}</p>
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

      <CtaBand title="Ready when you are" body="Start a trial or ask sales for a volume quote." />
    </>
  );
}
