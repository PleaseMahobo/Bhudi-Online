import Link from 'next/link';
import {
  ArrowRight,
  Building2,
  Monitor,
  ScreenShare,
  Shield,
  Terminal,
  Zap,
} from 'lucide-react';
import DeepBuddyLogo from '@/shared/deepbuddy/DeepBuddyLogo';

const FEATURES = [
  {
    icon: Building2,
    title: 'Clients & sites',
    body: 'Tactical-style org tree: client → site → agents. Assign endpoints without leaving the list.',
  },
  {
    icon: Monitor,
    title: 'Agent fleet',
    body: 'Online / offline / overdue status, inventory, processes, and software — one pane of glass.',
  },
  {
    icon: ScreenShare,
    title: 'Remote access',
    body: 'One-click remote desktop and terminal sessions through the Bhudi native agent.',
  },
  {
    icon: Terminal,
    title: 'Scripts & automation',
    body: 'Queue shell and package commands across Windows, Linux, and macOS agents.',
  },
  {
    icon: Shield,
    title: 'Security posture',
    body: 'MFA-ready console access, session-aware capture, and audit-friendly operations.',
  },
  {
    icon: Zap,
    title: 'Built for MSPs',
    body: 'Multi-tenant thinking from day one — scale from a lab box to a full practice.',
  },
];

export default function DeepBuddyHomePage() {
  return (
    <div className="min-h-screen bg-[#020617] text-slate-100">
      <header className="border-b border-white/10 bg-[#020617]/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <DeepBuddyLogo href="/deep-buddy" inverted />
          <nav className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
            <a href="#features" className="hover:text-white">
              Features
            </a>
            <a href="#stack" className="hover:text-white">
              Stack
            </a>
            <Link href="/deep-buddy/console" className="hover:text-white">
              Console
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="hidden rounded-lg px-3 py-2 text-sm text-slate-300 hover:text-white sm:inline"
            >
              Sign in
            </Link>
            <Link
              href="/deep-buddy/console"
              className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
            >
              Open console
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6">
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Cyber Bastion · Deep Buddy RMM
        </p>
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Tactical-class remote monitoring & management — branded for your practice.
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-400">
          Deep Buddy wraps the operational patterns you know from Tactical RMM — client/site trees,
          agent status, remote sessions, scripts — into a modern web console backed by the Bhudi
          Online agent runtime.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/deep-buddy/console"
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
          >
            Launch console
            <ArrowRight size={16} />
          </Link>
          <Link
            href="/agents"
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 px-5 py-3 text-sm font-medium text-white hover:bg-white/5"
          >
            Download agents
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm text-slate-400 hover:text-white"
          >
            Bhudi Online platform →
          </Link>
        </div>
      </section>

      <section id="features" className="border-t border-white/10 bg-slate-950/50 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-2xl font-semibold text-white">What Deep Buddy includes</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            UX inspired by Tactical RMM workflows — not a clone. Built to run on the same stack as
            Bhudi Online.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
                >
                  <Icon className="mb-3 text-cyan-400" size={22} />
                  <h3 className="font-semibold text-white">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="stack" className="border-t border-white/10 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-2xl font-semibold text-white">How it relates to Bhudi Online</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/5 p-6">
              <h3 className="font-semibold text-cyan-300">Deep Buddy</h3>
              <p className="mt-2 text-sm text-slate-300">
                Tactical-flavored RMM console and marketing site for MSPs who want client/site
                hierarchy, agent lists, and remote ops in a focused product skin.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h3 className="font-semibold text-white">Bhudi Online</h3>
              <p className="mt-2 text-sm text-slate-400">
                Full AI-powered IT operations platform — ticketing, security, billing, print, and
                more — sharing the same agents and backend.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 py-10 text-center text-xs text-slate-500">
        © {new Date().getFullYear()} Cyber Bastion · Deep Buddy RMM · Part of the Bhudi Online family
      </footer>
    </div>
  );
}
