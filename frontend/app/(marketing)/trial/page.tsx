import Link from 'next/link';
import { Check, ArrowRight } from 'lucide-react';
import { PageHero, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Start free trial — Bhudi',
  description: 'Set up Bhudi on your own PC and let a trusted helper connect when you need assistance.',
};

const STEPS = [
  'Create a free account (personal email is fine)',
  'Download the Windows agent and install once',
  'Stay signed in — the agent reconnects after reboot',
  'Share access with the person who helps you',
];

export default function TrialPage() {
  return (
    <>
      <PageHero
        label="Free trial"
        title="Remote help for your own computer"
        subtitle="Bhudi is for people who regularly need assistance with their PC — not only corporate IT. Install once, stay online, get help when you need it."
        primaryHref="/signup?plan=personal"
        primaryLabel="Create free account"
        secondaryHref="/pricing"
        secondaryLabel="See personal plans"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <SectionLabel>How it works</SectionLabel>
            <ul className="mt-6 space-y-3">
              {STEPS.map((s, i) => (
                <li key={s} className="flex items-start gap-3 text-slate-700">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  {s}
                </li>
              ))}
            </ul>
            <ul className="mt-8 space-y-2 text-sm text-slate-600">
              {[
                'No Python or complicated setup on your PC',
                'Agent starts at logon and restarts if it stops',
                'You control who can connect',
              ].map((t) => (
                <li key={t} className="flex gap-2">
                  <Check className="shrink-0 text-emerald-500" size={16} />
                  {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-bold text-[#0F172A]">Create your account</h2>
            <p className="mt-2 text-sm text-slate-600">
              Use a personal email. You can upgrade to Household later.
            </p>
            <Link
              href="/signup?plan=personal"
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              Sign up free
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/login"
              className="mt-3 inline-flex w-full items-center justify-center rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              Already have an account? Log in
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
