import Link from 'next/link';
import { Check, ArrowRight } from 'lucide-react';
import { PageHero, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Start free trial — Bhudi',
  description: 'Open a Bhudi workspace and deploy native agents to pilot devices.',
};

const INCLUDES = [
  'Access to the operations shell',
  'Native agent downloads (Windows, Linux, macOS)',
  'Remote desktop and terminal',
  'Device inventory and heartbeats',
  'Bhudi AI assistant (preview capacity)',
];

export default function TrialPage() {
  return (
    <>
      <PageHero
        label="Free trial"
        title="Pilot Bhudi on your terms"
        subtitle="Create a workspace, install agents on a handful of machines, and experience remote access, print visibility, and the modern shell — without a long procurement cycle."
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <SectionLabel>What you get</SectionLabel>
            <ul className="mt-6 space-y-3">
              {INCLUDES.map((item) => (
                <li key={item} className="flex items-start gap-2 text-slate-700">
                  <Check className="mt-0.5 shrink-0 text-emerald-500" size={18} />
                  {item}
                </li>
              ))}
            </ul>
            <p className="mt-6 text-sm text-slate-500">
              Need a guided pilot for an MSP multi-tenant scenario?{' '}
              <Link href="/contact" className="font-semibold text-indigo-600">
                Contact sales
              </Link>
              .
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-bold text-[#0F172A]">Create your workspace</h2>
            <p className="mt-2 text-sm text-slate-600">
              Use signup to register, or log in if you already have an account.
            </p>
            <div className="mt-6 flex flex-col gap-3">
              <Link
                href="/signup"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
              >
                Sign up for trial
                <ArrowRight size={16} />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center justify-center rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
              >
                Already registered? Log in
              </Link>
            </div>
            <ol className="mt-8 space-y-2 border-t border-slate-100 pt-6 text-sm text-slate-600">
              <li>1. Complete signup</li>
              <li>2. Open Agents and download an installer</li>
              <li>3. Run install once on a pilot PC</li>
              <li>4. Connect from Remote Access</li>
            </ol>
          </div>
        </div>
      </section>
    </>
  );
}
