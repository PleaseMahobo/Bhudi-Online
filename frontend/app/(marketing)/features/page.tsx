import Link from 'next/link';
import {
  Activity,
  Bot,
  Printer,
  Shield,
  Server,
  Ticket,
  Terminal,
  Package,
  Bell,
  ArrowRight,
} from 'lucide-react';

export const metadata = {
  title: 'Features — Bhudi',
  description: 'RMM, AI assistant, print management, endpoint security, ITSM, and automation.',
};

const FEATURES = [
  {
    id: 'ai',
    icon: Bot,
    title: 'Bhudi AI Assistant',
    body: 'Docked throughout the app. Ask about CPU spikes, missing KBs, failed MFA, or generate monthly compliance reports in natural language.',
  },
  {
    id: 'rmm',
    icon: Server,
    title: 'Device & RMM',
    body: 'Inventory, patching, scripts, remote access, and software deployment with clear health signals for every endpoint.',
  },
  {
    id: 'print',
    icon: Printer,
    title: 'Print Management',
    body: 'Print servers, queues, drivers, jobs, toner, and offline devices — including UniPrint, Universal Print, Printix, and PaperCut awareness.',
  },
  {
    id: 'security',
    icon: Shield,
    title: 'Endpoint Security',
    body: 'Providers, agents, findings, and security scores. Unify Defender, CrowdStrike, Huntress, Bitdefender, and more under one posture view.',
  },
  {
    id: 'itsm',
    icon: Ticket,
    title: 'Ticketing & ITSM',
    body: 'Service tickets linked to assets and alerts so technicians resolve from context, not another silo.',
  },
  {
    id: 'alerts',
    icon: Bell,
    title: 'Alert Engine',
    body: 'Rules, escalation policies, AI suppression, and live streams that cut noise without hiding real risk.',
  },
  {
    id: 'automation',
    icon: Terminal,
    title: 'Automation & Scripts',
    body: 'Repeatable runbooks and command workflows that scale across customers and sites.',
  },
  {
    id: 'assets',
    icon: Package,
    title: 'Assets & Lifecycle',
    body: 'Hardware inventory, vendors, licenses, contracts, warranty, and depreciation in one record.',
  },
  {
    id: 'ops',
    icon: Activity,
    title: 'Dashboards & Reporting',
    body: 'Executive views for MSPs and enterprise IT — health, risk, and capacity without spreadsheet archaeology.',
  },
];

export default function FeaturesPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold text-indigo-600">Features</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#0F172A]">
          Everything you need to run modern IT ops
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Inspired by the clarity of tools teams already trust — designed as Bhudi,
          not a lookalike. Depth where technicians live, calm where leaders look.
        </p>
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ id, icon: Icon, title, body }) => (
          <article
            key={id}
            id={id}
            className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
              <Icon size={20} />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p>
          </article>
        ))}
      </div>

      <div className="mt-16 rounded-2xl border border-slate-200 bg-slate-50 p-8 text-center">
        <p className="text-slate-700">See how these modules work together in your environment.</p>
        <Link
          href="/trial"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          Start Free Trial <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
