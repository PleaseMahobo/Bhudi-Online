import Link from 'next/link';
import {
  Activity,
  Bot,
  Printer,
  Shield,
  Server,
  Ticket,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

export const metadata = {
  title: 'Bhudi — AI-powered IT Operations Platform',
  description:
    'Monitor, manage, and secure endpoints for MSPs and Enterprise IT. RMM, ticketing, print management, and Bhudi AI in one platform.',
};

const PILLARS = [
  {
    icon: Activity,
    title: 'Monitor',
    body: 'Real-time device health, alerts, and security posture across every customer environment.',
  },
  {
    icon: Server,
    title: 'Manage',
    body: 'Patching, scripts, remote access, software deployment, and print operations from one console.',
  },
  {
    icon: Shield,
    title: 'Secure',
    body: 'Endpoint security scores, findings, and policy-driven response — with AI-assisted triage.',
  },
];

const MODULES = [
  {
    icon: Bot,
    title: 'Bhudi AI',
    body: 'Ask why a server is hot, find missing patches, or generate a compliance report in plain language.',
  },
  {
    icon: Printer,
    title: 'Print Management',
    body: 'Queues, drivers, toner, and offline printers — a differentiator built for real MSP workflows.',
  },
  {
    icon: Ticket,
    title: 'ITSM & Automation',
    body: 'Tickets, escalation, and runbooks that connect alerts to resolution without tool-hopping.',
  },
];

const TRUST = ['MSPs', 'Enterprise IT', 'Managed SOC teams', 'Hybrid environments'];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-slate-200 bg-gradient-to-b from-slate-50 to-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(37,99,235,0.12),_transparent_55%)]" />
        <div className="relative mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24">
          <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
            AI-powered IT Operations Platform
          </p>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-[#0F172A] sm:text-6xl sm:leading-[1.05]">
            Monitor.
            <br />
            Manage.
            <br />
            <span className="text-indigo-600">Secure.</span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg text-slate-600 leading-relaxed">
            The AI-powered IT Operations Platform for MSPs and Enterprise IT.
            One workspace for devices, tickets, print, security — and an assistant
            that understands your estate.
          </p>

          <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              href="/trial"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
            >
              Start Free Trial
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
            >
              Book a Demo
            </Link>
          </div>

          <div className="mt-14 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-500">
            <span className="font-medium text-slate-700">Trusted by MSPs and IT Teams</span>
            {TRUST.map((t) => (
              <span key={t} className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-500" />
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="grid gap-6 md:grid-cols-3">
          {PILLARS.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
            >
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-[#0F172A] text-indigo-300">
                <Icon size={20} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Modules */}
      <section className="border-y border-slate-200 bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight text-[#0F172A]">
              Built for how IT actually works
            </h2>
            <p className="mt-3 text-slate-600">
              Familiar RMM workflows — without looking like every other console.
              Bhudi pairs operational depth with a calm, modern interface and AI
              that stays in context.
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {MODULES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <Icon className="text-indigo-600" size={22} />
                <h3 className="mt-4 font-semibold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p>
              </div>
            ))}
          </div>

          <div className="mt-10">
            <Link
              href="/features"
              className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-600 hover:text-indigo-500"
            >
              Explore all features
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="overflow-hidden rounded-3xl bg-[#0F172A] px-8 py-14 text-center shadow-lg sm:px-16">
          <h2 className="text-3xl font-bold tracking-tight text-white">
            Ready to run IT with intelligence?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-slate-300">
            Start a free trial or book a demo with the Bhudi team. No clone of
            yesterday&apos;s RMM — a platform designed around how you work today.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/trial"
              className="inline-flex rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              Start Free Trial
            </Link>
            <Link
              href="/contact"
              className="inline-flex rounded-xl border border-slate-600 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-800"
            >
              Book a Demo
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
