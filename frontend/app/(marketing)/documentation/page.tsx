import Link from 'next/link';
import { BookOpen, Download, Server, Terminal, ArrowRight } from 'lucide-react';
import { PageHero, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Documentation — Bhudi',
  description: 'Deploy agents, open remote sessions, and operate the Bhudi workspace.',
};

const GUIDES = [
  {
    icon: Download,
    title: 'Install the agent',
    body: 'Windows GUI installer, Linux binaries, and macOS builds. No Python on the endpoint.',
    href: '/agents',
  },
  {
    icon: Server,
    title: 'Enroll & heartbeat',
    body: 'Agents enroll against the runtime API, persist identity, and reconnect after reboot.',
    href: '/agents',
  },
  {
    icon: Terminal,
    title: 'Remote desktop & terminal',
    body: 'Select a device, choose a display, connect, and control with fit-to-page viewing.',
    href: '/remote',
  },
  {
    icon: BookOpen,
    title: 'Platform modules',
    body: 'Dashboard, devices, print, tickets, security, automation, and Bhudi AI overview.',
    href: '/features',
  },
];

const STEPS = [
  { t: 'Create a workspace', d: 'Sign up or start a trial and sign in to the app shell.' },
  { t: 'Download an agent', d: 'From Agents, pick Windows, Linux, or macOS and download.' },
  {
    t: 'Install on the endpoint',
    d: 'Windows: download BhudiAgent-Setup.exe from the Bhudi Agents page, double-click it, approve UAC, and complete the setup wizard. No command-line installation is required.',
  },
  { t: 'Confirm online', d: 'Device appears online after the first heartbeat.' },
  { t: 'Remote in', d: 'Open Remote Access, select display, Connect.' },
];

export default function DocumentationPage() {
  return (
    <>
      <PageHero
        label="Documentation"
        title="Get from zero to remote session quickly"
        subtitle="Practical guides for deploying the native agent and using the operations shell."
        primaryHref="/agents"
        primaryLabel="Agent downloads"
        secondaryHref="/trial"
        secondaryLabel="Start trial"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <SectionLabel>Guides</SectionLabel>
        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          {GUIDES.map(({ icon: Icon, title, body, href }) => (
            <Link
              key={title}
              href={href}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
            >
              <Icon className="text-indigo-600" size={22} />
              <h2 className="mt-4 text-lg font-semibold text-slate-900">{title}</h2>
              <p className="mt-2 text-sm text-slate-600">{body}</p>
              <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-indigo-600">
                Open <ArrowRight size={12} />
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="border-t border-slate-100 bg-slate-50">
        <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
          <SectionLabel>Quick start</SectionLabel>
          <h2 className="mt-2 text-2xl font-bold text-[#0F172A]">Five steps</h2>
          <ol className="mt-8 space-y-4">
            {STEPS.map((s, i) => (
              <li key={s.t} className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-5">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">
                  {i + 1}
                </span>
                <div>
                  <h3 className="font-semibold text-slate-900">{s.t}</h3>
                  <p className="mt-1 text-sm text-slate-600">{s.d}</p>
                </div>
              </li>
            ))}
          </ol>
          <pre className="mt-8 overflow-x-auto rounded-xl bg-slate-900 p-4 text-xs text-slate-200">{
`# Windows\nDownload BhudiAgent-Setup.exe from the Bhudi portal → double-click → approve UAC → complete the setup wizard\n\n# Linux\nchmod +x bhudi-agent-linux-amd64\nsudo ./bhudi-agent-linux-amd64 install -server https://bhudi-online-production.up.railway.app`
          }</pre>
        </div>
      </section>
    </>
  );
}
