import Link from 'next/link';
import { Building2, Headphones, Network, ShieldCheck, ArrowRight } from 'lucide-react';
import { PageHero, CtaBand, SectionLabel } from '@/shared/marketing/MarketingUI';

export const metadata = {
  title: 'Solutions — Bhudi',
  description: 'Bhudi for MSPs, enterprise IT, hybrid environments, and security-aligned operations.',
};

const SOLUTIONS = [
  {
    icon: Headphones,
    title: 'Managed service providers',
    body: 'Multi-tenant ready operations: enroll customer devices, remote in, manage print fleets, and keep technicians in one shell per ticket.',
    points: ['Per-customer device estates', 'Fast remote desktop & terminal', 'Agent installers for Windows, Linux, macOS'],
  },
  {
    icon: Building2,
    title: 'Enterprise IT',
    body: 'Central visibility for distributed offices, shared print infrastructure, and consistent automation without bolting on five consoles.',
    points: ['Single pane for health and alerts', 'Print servers and queues as first-class objects', 'AI-assisted investigation'],
  },
  {
    icon: Network,
    title: 'Hybrid & remote workforces',
    body: 'Support laptops and branch devices when users are online — with agents that survive reboot and reconnect automatically.',
    points: ['Install once, auto-start at logon', 'Interactive session capture', 'Secure session WebSockets'],
  },
  {
    icon: ShieldCheck,
    title: 'Security operations alignment',
    body: 'Keep endpoint posture and findings next to the same devices you patch and remote into — shorter handoffs between IT and security.',
    points: ['Endpoint security module', 'Partner tool surface area', 'Audit-friendly command history'],
  },
];

export default function SolutionsPage() {
  return (
    <>
      <PageHero
        label="Solutions"
        title="One platform, tuned to how you deliver IT"
        subtitle="Whether you support hundreds of customers or a single large estate, Bhudi is shaped around technician workflow — not a checklist of disconnected modules."
        primaryHref="/contact"
        primaryLabel="Talk to us"
        secondaryHref="/pricing"
        secondaryLabel="See pricing"
      />

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-8">
          {SOLUTIONS.map(({ icon: Icon, title, body, points }) => (
            <article
              key={title}
              className="grid gap-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm lg:grid-cols-[auto_1fr_auto] lg:items-start"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                <Icon size={24} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-[#0F172A]">{title}</h2>
                <p className="mt-2 text-slate-600 leading-relaxed">{body}</p>
                <ul className="mt-4 flex flex-wrap gap-2">
                  {points.map((p) => (
                    <li
                      key={p}
                      className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
                    >
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
              <Link
                href="/trial"
                className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-500"
              >
                Try Bhudi <ArrowRight size={14} />
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="border-t border-slate-100 bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <SectionLabel>Implementation</SectionLabel>
          <h2 className="mt-2 text-2xl font-bold text-[#0F172A]">Typical rollout</h2>
          <ol className="mt-8 grid gap-4 md:grid-cols-4">
            {[
              ['1', 'Trial workspace', 'Create your tenant and invite technicians.'],
              ['2', 'Deploy agents', 'Push EXE/MSI or Linux/macOS binaries to endpoints.'],
              ['3', 'Connect modules', 'Turn on remote, print, tickets, and security views.'],
              ['4', 'Operate', 'Use the shell daily; expand automation and AI prompts.'],
            ].map(([n, t, b]) => (
              <li key={n} className="rounded-2xl border border-slate-200 bg-white p-5">
                <span className="text-xs font-bold text-indigo-500">Step {n}</span>
                <h3 className="mt-2 font-semibold">{t}</h3>
                <p className="mt-1 text-sm text-slate-600">{b}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <CtaBand title="See Bhudi on your use case" body="Book a demo and we will map modules to your MSP or enterprise workflow." />
    </>
  );
}
