import Link from 'next/link';
import { Check } from 'lucide-react';
import { PageHero, CtaBand, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Pricing — Bhudi',
  description: 'Plans for individuals who need ongoing PC help, households, and small support practices.',
};

const PLANS = [
  {
    name: 'Personal',
    price: '$9',
    period: 'per month',
    blurb: 'For one person who wants trusted remote help on their own PC whenever they need it.',
    features: [
      '1 registered computer',
      'Native Windows agent (install once)',
      'Remote desktop & terminal for your helper',
      'Stays connected after reboot',
      'Email support',
    ],
    cta: 'Start personal trial',
    href: '/signup?plan=personal',
    highlighted: false,
  },
  {
    name: 'Household',
    price: '$19',
    period: 'per month',
    blurb: 'Parents, partners, or a helper who regularly assists a few family computers.',
    features: [
      'Up to 5 computers',
      'Invite one trusted helper',
      'Remote access per device',
      'Basic alerts & device status',
      'Priority email support',
    ],
    cta: 'Start household trial',
    href: '/signup?plan=household',
    highlighted: true,
  },
  {
    name: 'Helper Pro',
    price: '$39',
    period: 'per month',
    blurb: 'Independent helpers and small shops supporting multiple clients’ PCs — without enterprise complexity.',
    features: [
      'Up to 25 computers',
      'Multiple client folders',
      'Remote desktop & terminal',
      'Print & device basics',
      'Chat / email support',
    ],
    cta: 'Start helper trial',
    href: '/signup?plan=helper',
    highlighted: false,
  },
];

const FAQ = [
  {
    q: 'Is this only for companies?',
    a: 'No. Bhudi is built so individuals can install an agent on their PC and let a trusted person connect securely when help is needed.',
  },
  {
    q: 'Do I need to reinstall every time?',
    a: 'No. Install once. The agent starts at logon and a watchdog restarts it if it stops.',
  },
  {
    q: 'Does my PC need Python?',
    a: 'No. The agent is a normal Windows program.',
  },
  {
    q: 'What about businesses?',
    a: 'Larger estates can contact us for volume pricing. Plans above are aimed at personal and small-helper use first.',
  },
];

export default function PricingPage() {
  return (
    <>
      <PageHero
        label="Pricing"
        title="Help with your computer — without enterprise pricing"
        subtitle="Built for people who regularly need remote assistance on their own PCs, and for the helpers who support them."
        primaryHref="/signup?plan=personal"
        primaryLabel="Create free account"
        secondaryHref="/contact"
        secondaryLabel="Ask a question"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <p className="mb-8 text-center text-sm text-slate-500">
          USD · cancel anytime · trial available on all plans
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
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{plan.period}</p>
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

      <CtaBand
        title="Install once. Get help whenever you need it."
        body="Create an account, put the agent on your PC, and invite the person who helps you."
        primaryHref="/signup?plan=personal"
        primaryLabel="Create account"
        secondaryHref="/agents"
        secondaryLabel="Download agent"
      />
    </>
  );
}
