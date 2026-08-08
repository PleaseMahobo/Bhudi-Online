'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { AlertTriangle, Bell, CheckCircle2, Info, Ticket, X } from 'lucide-react';

type Notification = { id: string; title: string; detail: string; href: string; tone: 'critical' | 'warning' | 'info' | 'success'; time: string };

const INITIAL: Notification[] = [
  { id: 'critical-1', title: 'Critical attention required', detail: 'Review offline devices and urgent operational signals.', href: '/alert-engine', tone: 'critical', time: 'Now' },
  { id: 'ticket-1', title: 'Ticket workload needs review', detail: 'Open the ITSM queue to review active work.', href: '/itsm', tone: 'warning', time: 'Today' },
  { id: 'security-1', title: 'Security posture available', detail: 'Review endpoint security coverage and findings.', href: '/endpoint-security', tone: 'info', time: 'Today' },
  { id: 'success-1', title: 'Bhudi is connected', detail: 'The application shell is receiving live status.', href: '/dashboard', tone: 'success', time: 'Today' },
];

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(INITIAL);
  const unread = items.length;
  const tones = useMemo(() => ({
    critical: { icon: AlertTriangle, bg: 'bg-red-50', text: 'text-red-600' },
    warning: { icon: Ticket, bg: 'bg-amber-50', text: 'text-amber-600' },
    info: { icon: Info, bg: 'bg-sky-50', text: 'text-sky-600' },
    success: { icon: CheckCircle2, bg: 'bg-emerald-50', text: 'text-emerald-600' },
  }), []);

  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)} className="relative h-9 w-9 rounded-lg text-slate-500 hover:bg-slate-100" aria-label="Notifications" aria-expanded={open}>
        <Bell size={18} className="mx-auto" />
        {unread > 0 && <span className="absolute right-0.5 top-0.5 flex min-h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white ring-2 ring-white">{unread > 9 ? '9+' : unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-50 w-[360px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3"><div><p className="text-sm font-semibold text-slate-900">Notifications</p><p className="text-xs text-slate-500">{unread} items need attention</p></div><div className="flex items-center gap-1"><button type="button" onClick={() => setItems([])} className="rounded-lg px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50">Mark all read</button><button type="button" onClick={() => setOpen(false)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100" aria-label="Close"><X size={16} /></button></div></div>
          <div className="max-h-[420px] overflow-y-auto">
            {items.length ? items.map((item) => { const tone = tones[item.tone]; const Icon = tone.icon; return <Link key={item.id} href={item.href} onClick={() => setOpen(false)} className="flex gap-3 border-b border-slate-100 px-4 py-3 hover:bg-slate-50"><span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${tone.bg} ${tone.text}`}><Icon size={15} /></span><span className="min-w-0 flex-1"><span className="flex justify-between gap-2"><span className="text-sm font-medium text-slate-900">{item.title}</span><span className="shrink-0 text-[10px] text-slate-400">{item.time}</span></span><span className="mt-0.5 block text-xs leading-5 text-slate-500">{item.detail}</span></span></Link>; }) : <div className="px-4 py-10 text-center"><CheckCircle2 className="mx-auto text-emerald-500" size={25} /><p className="mt-2 text-sm font-medium text-slate-900">All caught up</p><p className="mt-1 text-xs text-slate-500">No unread notifications.</p></div>}
          </div>
        </div>
      )}
    </div>
  );
}
