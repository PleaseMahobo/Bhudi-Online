import Link from 'next/link';
import { Activity, ArrowRight, Bot, CheckCircle2, ChevronRight, Cloud, Monitor, Printer, Shield, Sparkles, Ticket, Zap } from 'lucide-react';

export const metadata = {
  title: 'Bhudi — Intelligent IT Operations Platform',
  description: 'Monitor, manage, secure, and automate IT environments from one intelligent operations platform for MSPs and enterprise IT teams.',
};

const CAPABILITIES = [
  { icon: Monitor, title: 'RMM & Device Management', body: 'See device health, availability, performance, software, and operational status from one workspace.' },
  { icon: Ticket, title: 'ITSM & Ticketing', body: 'Connect service requests, alerts, priorities, and technician workflows without switching consoles.' },
  { icon: Shield, title: 'Endpoint Security', body: 'Bring security posture, endpoint protection, findings, and response into the operational view.' },
  { icon: Printer, title: 'Print Management', body: 'Manage printers, queues, drivers, and print health across mixed vendor environments.' },
  { icon: Zap, title: 'Automation & Patching', body: 'Turn repetitive maintenance into controlled jobs, scripts, policies, and remediation workflows.' },
  { icon: Bot, title: 'Bhudi AI', body: 'Ask operational questions in plain language and move from investigation to action faster.' },
];

const WORKFLOW = [
  ['01', 'Discover', 'Bring devices, users, services, printers, and security signals into one estate view.'],
  ['02', 'Understand', 'Prioritize what needs attention with health, alerts, tickets, and security context.'],
  ['03', 'Act', 'Run scripts, patch devices, manage printers, respond to incidents, and resolve tickets.'],
  ['04', 'Improve', 'Use reporting and AI-assisted insights to continuously improve the environment.'],
];

const TRUST = ['MSPs', 'Enterprise IT', 'Hybrid environments', 'Distributed teams'];

export default function HomePage() {
  return (
    <main className="bg-white text-slate-900">
      <section className="relative overflow-hidden bg-[#08111f] text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,rgba(79,70,229,0.28),transparent_34%),radial-gradient(circle_at_85%_20%,rgba(14,165,233,0.16),transparent_30%)]" />
        <div className="relative mx-auto grid max-w-7xl gap-14 px-4 pb-24 pt-16 sm:px-6 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:pb-28 lg:pt-24">
          <div>
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-400/10 px-3 py-1.5 text-xs font-semibold text-indigo-200"><Sparkles size={14} /> Intelligent IT Operations</div>
            <h1 className="max-w-3xl text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl lg:leading-[1.02]">One console for your entire IT estate.</h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-300 sm:text-xl">Bhudi brings monitoring, ticketing, automation, endpoint security, print management, and AI-assisted operations into one calm workspace.</p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row"><Link href="/trial" className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 hover:bg-indigo-400">Start Free Trial <ArrowRight size={17} /></Link><Link href="/contact" className="inline-flex items-center justify-center rounded-xl border border-slate-600 bg-white/5 px-6 py-3.5 text-sm font-semibold text-white hover:bg-white/10">Book a Demo</Link></div>
            <div className="mt-10 flex flex-wrap gap-x-6 gap-y-3 text-sm text-slate-400">{TRUST.map((item) => <span key={item} className="inline-flex items-center gap-2"><CheckCircle2 size={14} className="text-emerald-400" />{item}</span>)}</div>
          </div>
          <div className="relative rounded-2xl border border-white/10 bg-white/[0.06] p-3 shadow-2xl shadow-black/30 backdrop-blur"><div className="rounded-xl border border-white/10 bg-slate-950/80 p-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-4"><div><p className="text-xs text-slate-400">Bhudi Workspace</p><p className="mt-1 font-semibold">Operations overview</p></div><span className="rounded-full bg-emerald-400/10 px-2 py-1 text-[11px] font-medium text-emerald-300">● Live</span></div>
            <div className="grid grid-cols-2 gap-3 py-4 sm:grid-cols-4">{[['Devices', '1,245'], ['Online', '1,203'], ['Alerts', '18'], ['Tickets', '37']].map(([label, value]) => <div key={label} className="rounded-xl bg-white/[0.05] p-3"><p className="text-[11px] text-slate-500">{label}</p><p className="mt-1 text-xl font-semibold">{value}</p></div>)}</div>
            <div className="grid gap-3 sm:grid-cols-[1.15fr_.85fr]"><div className="rounded-xl border border-white/10 bg-white/[0.04] p-4"><div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-300">Estate health</span><Activity size={15} className="text-indigo-300" /></div><div className="mt-5 flex h-24 items-end gap-1">{[28,42,35,58,51,68,62,78,72,88,81,94].map((height, i) => <div key={i} className="flex-1 rounded-t bg-indigo-500/70" style={{ height: `${height}%` }} />)}</div></div><div className="rounded-xl border border-white/10 bg-white/[0.04] p-4"><p className="text-xs font-medium text-slate-300">Attention</p><div className="mt-4 space-y-3 text-xs"><div className="flex justify-between"><span className="text-slate-400">Critical</span><b className="text-red-300">4</b></div><div className="flex justify-between"><span className="text-slate-400">Warning</span><b className="text-amber-300">14</b></div><div className="flex justify-between"><span className="text-slate-400">Patch ready</span><b className="text-sky-300">86</b></div></div></div></div>
            <div className="mt-3 flex items-center gap-3 rounded-xl border border-indigo-400/20 bg-indigo-400/10 p-3"><Bot size={18} className="text-indigo-300" /><div><p className="text-xs font-semibold">Ask Bhudi</p><p className="text-[11px] text-slate-400">“What needs attention today?”</p></div><ChevronRight size={15} className="ml-auto text-slate-500" /></div>
          </div></div>
        </div>
      </section>
      <section className="border-b border-slate-200 bg-slate-50"><div className="mx-auto grid max-w-7xl gap-5 px-4 py-8 sm:grid-cols-3 sm:px-6">{[['Monitor', 'Know what is happening across every device and customer.'], ['Manage', 'Resolve work from tickets to patching to print operations.'], ['Secure', 'Make security posture part of everyday IT operations.']].map(([title, body]) => <div key={title} className="flex gap-4 rounded-xl bg-white p-5 shadow-sm"><div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-indigo-500" /><div><h2 className="font-semibold">{title}</h2><p className="mt-1 text-sm leading-6 text-slate-600">{body}</p></div></div>)}</div></section>
      <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6"><div className="max-w-2xl"><p className="text-sm font-semibold text-indigo-600">ONE OPERATIONS PLATFORM</p><h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Everything your technicians need, without the console sprawl.</h2><p className="mt-4 leading-7 text-slate-600">A familiar RMM experience, expanded around the real work of modern IT teams.</p></div><div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{CAPABILITIES.map(({ icon: Icon, title, body }) => <div key={title} className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md"><div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"><Icon size={21} /></div><h3 className="mt-5 font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{body}</p><span className="mt-5 inline-flex items-center gap-1 text-xs font-semibold text-indigo-600">Learn more <ArrowRight size={13} /></span></div>)}</div></section>
      <section className="border-y border-slate-200 bg-slate-50"><div className="mx-auto max-w-7xl px-4 py-24 sm:px-6"><div className="max-w-2xl"><p className="text-sm font-semibold text-indigo-600">THE BHUDI WORKFLOW</p><h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">From signal to resolution.</h2></div><div className="mt-12 grid gap-5 md:grid-cols-4">{WORKFLOW.map(([number, title, body]) => <div key={number} className="relative rounded-2xl border border-slate-200 bg-white p-6"><span className="text-xs font-bold text-indigo-500">{number}</span><h3 className="mt-5 font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{body}</p></div>)}</div></div></section>
      <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6"><div className="rounded-3xl bg-[#0F172A] px-6 py-14 text-center shadow-xl sm:px-12"><Cloud className="mx-auto text-indigo-300" size={28} /><h2 className="mx-auto mt-5 max-w-2xl text-3xl font-bold tracking-tight text-white sm:text-4xl">Run IT from one intelligent workspace.</h2><p className="mx-auto mt-4 max-w-xl leading-7 text-slate-300">Bring your operations together and give technicians a faster path from alert to action.</p><div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row"><Link href="/trial" className="rounded-xl bg-indigo-500 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-400">Start Free Trial</Link><Link href="/contact" className="rounded-xl border border-slate-600 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-800">Book a Demo</Link></div></div></section>
    </main>
  );
}
