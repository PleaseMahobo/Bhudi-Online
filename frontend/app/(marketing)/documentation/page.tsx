import Link from 'next/link';
import { BookOpen, Code2, Rocket, Shield } from 'lucide-react';

export const metadata = {
  title: 'Documentation — Bhudi',
  description: 'Guides, API references, and operational docs for Bhudi.',
};

const SECTIONS = [
  {
    icon: Rocket,
    title: 'Getting started',
    body: 'Create your workspace, connect agents, and invite your team.',
  },
  {
    icon: BookOpen,
    title: 'Operator guides',
    body: 'Devices, alerts, tickets, print, and security day-to-day workflows.',
  },
  {
    icon: Shield,
    title: 'Security & compliance',
    body: 'Posture scoring, findings lifecycle, and reporting for audits.',
  },
  {
    icon: Code2,
    title: 'API & automation',
    body: 'Authenticate, query assets, and drive automations programmatically.',
  },
];

export default function DocumentationPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold text-indigo-600">Documentation</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
          Learn Bhudi at your pace
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Product docs are expanding with the platform. Start here, or jump into
          the app with a trial workspace.
        </p>
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-2">
        {SECTIONS.map(({ icon: Icon, title, body }) => (
          <div
            key={title}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <Icon className="text-indigo-600" size={22} />
            <h2 className="mt-4 text-lg font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm text-slate-600">{body}</p>
          </div>
        ))}
      </div>

      <div className="mt-12 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
        <p className="text-slate-700">
          Full public docs portal is in progress. Prefer a guided walkthrough?
        </p>
        <Link
          href="/contact"
          className="mt-4 inline-flex rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          Book a Demo
        </Link>
      </div>
    </div>
  );
}
