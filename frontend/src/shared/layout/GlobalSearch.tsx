'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { Search, Monitor, Ticket, Users, ArrowRight, Command } from 'lucide-react';
import { getDevices, listTickets, type ServiceTicket } from '@/lib/api';

type Device = { id: string; hostname?: string; name?: string; status?: string };
type Result = { type: 'device' | 'ticket' | 'customer' | 'navigation'; title: string; subtitle: string; href: string };

const NAVIGATION: Result[] = [
  { type: 'navigation', title: 'Dashboard', subtitle: 'Operations command center', href: '/dashboard' },
  { type: 'navigation', title: 'Endpoint Security', subtitle: 'Security posture and protection', href: '/endpoint-security' },
  { type: 'navigation', title: 'Print Management', subtitle: 'Printers and print operations', href: '/assets' },
  { type: 'navigation', title: 'Reports', subtitle: 'Operational reporting', href: '/reporting' },
  { type: 'navigation', title: 'Automation', subtitle: 'Commands and automation', href: '/commands' },
];

export default function GlobalSearch() {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [tickets, setTickets] = useState<ServiceTicket[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (event: MouseEvent) => { if (!ref.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        (ref.current?.querySelector('input') as HTMLInputElement | null)?.focus();
        setOpen(true);
      }
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (!open || query.trim().length < 2) return;
    const timer = window.setTimeout(async () => {
      const [deviceResult, ticketResult] = await Promise.all([getDevices().catch(() => []), listTickets().catch(() => [] as ServiceTicket[])]);
      setDevices(Array.isArray(deviceResult) ? deviceResult : []);
      setTickets(Array.isArray(ticketResult) ? ticketResult : []);
    }, 180);
    return () => window.clearTimeout(timer);
  }, [open, query]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    const matches: Result[] = [];
    for (const d of devices) {
      const name = d.hostname || d.name || d.id;
      if (`${name} ${d.status || ''}`.toLowerCase().includes(q)) matches.push({ type: 'device', title: name, subtitle: `Device · ${d.status || 'unknown'}`, href: '/assets' });
      if (matches.filter((x) => x.type === 'device').length >= 5) break;
    }
    for (const t of tickets) {
      const text = `${t.title || ''} ${(t as any).number || ''} ${t.status || ''} ${t.priority || ''}`.toLowerCase();
      if (text.includes(q)) matches.push({ type: 'ticket', title: t.title || 'Untitled ticket', subtitle: `Ticket · ${(t.status || 'unknown').replace(/_/g, ' ')}`, href: '/itsm' });
      if (matches.filter((x) => x.type === 'ticket').length >= 5) break;
    }
    matches.push(...NAVIGATION.filter((item) => `${item.title} ${item.subtitle}`.toLowerCase().includes(q)).slice(0, 4));
    return matches.slice(0, 10);
  }, [query, devices, tickets]);

  return (
    <div ref={ref} className="relative min-w-0 flex-1 max-w-2xl">
      <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={17} />
      <input value={query} onChange={(event) => { setQuery(event.target.value); setOpen(true); }} onFocus={() => setOpen(true)} placeholder="Search devices, customers, tickets..." aria-label="Global search" className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-16 text-sm text-slate-900 outline-none transition focus:border-indigo-300 focus:bg-white focus:ring-2 focus:ring-indigo-100" />
      <kbd className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-400 sm:inline-flex"><Command size={10} /> K</kbd>
      {open && query.trim().length >= 2 && (
        <div className="absolute left-0 right-0 top-12 z-50 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
          {results.length ? results.map((result) => {
            const Icon = result.type === 'device' ? Monitor : result.type === 'ticket' ? Ticket : result.type === 'customer' ? Users : ArrowRight;
            return <Link key={`${result.type}-${result.href}-${result.title}`} href={result.href} onClick={() => setOpen(false)} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500"><Icon size={15} /></span><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium text-slate-900">{result.title}</span><span className="block truncate text-xs text-slate-500">{result.subtitle}</span></span><ArrowRight size={14} className="text-slate-300" /></Link>;
          }) : <div className="px-4 py-6 text-center text-sm text-slate-500">No matching devices, tickets, or workspace areas.</div>}
        </div>
      )}
    </div>
  );
}
