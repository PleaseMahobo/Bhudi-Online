import {
  Bot,
  Monitor,
  Printer,
  Shield,
  Terminal,
  Ticket,
  Zap,
  LayoutDashboard,
  Network,
  FileBarChart,
  KeyRound,
  Smartphone,
} from 'lucide-react';
import { PageHero, FeatureCard, CtaBand, SectionLabel, CheckList } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Features — Bhudi',
  description:
    'RMM, remote access, print management, ITSM, security, automation, and Bhudi AI in one platform.',
};

const MODULES = [
  {
    icon: LayoutDashboard,
    title: 'Executive dashboard',
    body: 'Estate health, open tickets, critical alerts, and AI summaries at a glance for technicians and managers.',
  },
  {
    icon: Monitor,
    title: 'Device management',
    body: 'Inventory, status, software, and performance across Windows, Linux, and macOS with a native agent.',
  },
  {
    icon: Terminal,
    title: 'Remote access',
    body: 'In-browser remote desktop and terminal. Select a monitor, fit to page, and control with accurate input mapping.',
  },
  {
    icon: Printer,
    title: 'Print management',
    body: 'Servers, queues, drivers, jobs, paper and toner levels, offline devices, and vendor integrations.',
  },
  {
    icon: Ticket,
    title: 'Ticketing & ITSM',
    body: 'Service tickets linked to devices and alerts so context travels with every work item.',
  },
  {
    icon: Shield,
    title: 'Endpoint security',
    body: 'Posture, findings, and partner tools (CrowdStrike, Huntress, Bitdefender, and more) in the ops view.',
  },
  {
    icon: Zap,
    title: 'Automation & scripts',
    body: 'Scheduled jobs, remediation scripts, and policy-driven actions with audit-friendly history.',
  },
  {
    icon: Network,
    title: 'Patching',
    body: 'Track missing updates, plan windows, and verify completion across the estate.',
  },
  {
    icon: Bot,
    title: 'Bhudi AI assistant',
    body: 'Docked assistant for high CPU, missing KBs, spooler restarts, and MFA failures in plain language.',
  },
  {
    icon: FileBarChart,
    title: 'Reporting',
    body: 'Compliance and operational reports you can generate on demand or on a schedule.',
  },
  {
    icon: KeyRound,
    title: 'Identity & access',
    body: 'Login, trial signup, and role-aware workspaces designed for MSP multi-tenant use.',
  },
  {
    icon: Smartphone,
    title: 'Agent lifecycle',
    body: 'Download EXE, Linux, and macOS agents. Install once — auto-start at logon and reconnect.',
  },
];

export default function FeaturesPage() {
  return (
    <>
      <PageHero
        label="Features"
        title="An operations platform, not a pile of tools"
        subtitle="Bhudi combines RMM depth, remote control, print management, and AI assistance in a single modern shell — so technicians spend less time switching context."
        primaryHref="/trial"
        primaryLabel="Start free trial"
        secondaryHref="/documentation"
        secondaryLabel="Read docs"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <SectionLabel>Modules</SectionLabel>
        <h2 className="mt-2 text-2xl font-bold text-[#0F172A] sm:text-3xl">
          Built for day-to-day MSP and enterprise work
        </h2>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m) => (
            <FeatureCard key={m.title} {...m} />
          ))}
        </div>
      </section>

      <section className="border-y border-slate-100 bg-slate-50">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-2">
          <div>
            <SectionLabel>Remote control</SectionLabel>
            <h2 className="mt-2 text-2xl font-bold text-[#0F172A]">
              See one screen. Click where you mean to.
            </h2>
            <p className="mt-3 text-slate-600">
              Choose Display 1, Display 2, or primary. Frames fit the page without breaking click
              accuracy. Terminal sessions use the same device list.
            </p>
          </div>
          <CheckList
            items={[
              'Native JPEG stream over secure WebSocket sessions',
              'Per-monitor capture (not a stretched dual-desktop blob)',
              'Mouse and keyboard mapped through scaled frames',
              'Fit page / fit width / fullscreen viewer controls',
              'Agent runs in the interactive user session for real desktop access',
            ]}
          />
        </div>
      </section>

      <CtaBand
        title="Put these features to work on your estate"
        body="Start a trial, deploy the agent, and open the operations shell in minutes."
      />
    </>
  );
}
