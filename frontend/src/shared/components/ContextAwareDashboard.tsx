'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, CircleAlert, Monitor, RefreshCw, Server, ShieldCheck, Ticket, Wifi } from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import { useAuth } from '@/shared/auth/AuthContext';
import { useWorkspace } from '@/shared/context/WorkspaceContext';
import { getDevices, listTickets, type ServiceTicket } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';

type Row = Record<string, any>;
const resolved = (s?: string) => ['resolved', 'closed', 'done', 'cancelled'].includes((s || '').toLowerCase());
const pending = (s?: string) => ['pending', 'waiting', 'on_hold', 'on-hold', 'customer_pending'].includes((s || '').toLowerCase());
const days = (v?: string | null) => { if (!v) return null; const t = new Date(v).getTime(); return Number.isNaN(t) ? null : Math.floor((t - Date.now()) / 86400000); };

function matchesScope(row: Row, organizationId: string | null, siteId: string | null, tenantId?: string) {
  if (!organizationId && !siteId) return true;
  const organizationCandidates = [row.organization_id, row.organizationId].filter(Boolean).map(String);
  const siteCandidates = [row.site_id, row.siteId].filter(Boolean).map(String);
  const tenantCandidates = [row.tenant_id, row.tenantId].filter(Boolean).map(String);
  if (siteId) return siteCandidates.includes(String(siteId));
  return organizationCandidates.includes(String(organizationId)) || (!!tenantId && tenantCandidates.includes(String(tenantId)));
}

function Card({ title, children, icon }: { title: string; children: React.ReactNode; icon?: React.ReactNode }) {
  return <section className="rounded-2xl border border-slate-200 bg-white shadow-sm"><header className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-sm font-semibold text-slate-900">{icon}{title}</header><div className="p-5">{children}</div></section>;
}

export default function ContextAwareDashboard() {
  const { user, loading: authLoading } = useAuth();
  const { organization, site, organizationId, siteId, loading: workspaceLoading } = useWorkspace();
  const { isConnected } = useWebSocket();
  const [devices, setDevices] = useState<Row[]>([]);
  const [tickets, setTickets] = useState<ServiceTicket[]>([]);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    const [d, t] = await Promise.all([getDevices().catch(() => []), listTickets().catch(() => [] as ServiceTicket[])]);
    setDevices(Array.isArray(d) ? d as Row[] : []);
    setTickets(Array.isArray(t) ? t : []);
    setBusy(false);
    setLoaded(true);
  }, []);

  useEffect(() => { if (!authLoading && user) void load(); }, [authLoading, user, load]);
  useEffect(() => { if (!authLoading && !workspaceLoading && user) void load(); }, [organizationId, siteId, authLoading, workspaceLoading, user, load]);

  const scopedDevices = useMemo(() => devices.filter((d) => matchesScope(d, organizationId, siteId, organization?.tenant_id)), [devices, organizationId, siteId, organization?.tenant_id]);
  const scopedTickets = useMemo(() => tickets.filter((t) => matchesScope(t as Row, organizationId, siteId, organization?.tenant_id)), [tickets, organizationId, siteId, organization?.tenant_id]);
  const hasScopedRecords = scopedDevices.length > 0 || scopedTickets.length > 0;
  const stats = useMemo(() => {
    const online = scopedDevices.filter((d) => d.online === true || String(d.status || '').toLowerCase() === 'online').length;
    const active = scopedTickets.filter((t) => !resolved(t.status));
    const critical = active.filter((t) => ['critical', 'urgent', 'p1'].includes(String(t.priority || '').toLowerCase())).length;
    const high = active.filter((t) => ['high', 'warning', 'p2'].includes(String(t.priority || '').toLowerCase())).length;
    const due = active.filter((t) => days((t as any).due_at || (t as any).due_date || (t as any).sla_due_at) === 0).length;
    const overdue = active.filter((t) => { const d = days((t as any).due_at || (t as any).due_date || (t as any).sla_due_at); return d !== null && d < 0; }).length;
    return { total: scopedDevices.length, online, offline: Math.max(0, scopedDevices.length - online), active: active.length, open: active.filter((t) => !pending(t.status)).length, pending: active.filter((t) => pending(t.status)).length, critical, high, due, overdue };
  }, [scopedDevices, scopedTickets]);

  const scopeLabel = site?.name ? `${organization?.name || 'Customer'} · ${site.name}` : organization?.name || 'All Customers';
  if (authLoading || workspaceLoading) return <ModuleShell title="Operations Center"><div className="text-sm text-slate-500">Loading workspace…</div></ModuleShell>;

  return <ModuleShell title="Operations Center" subtitle="Context-aware operational view across devices, tickets and alerts">
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-2xl border border-indigo-100 bg-indigo-50/70 p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-500">Current scope</p><p className="mt-1 text-sm font-semibold text-slate-900">{scopeLabel}</p><p className="mt-0.5 text-xs text-slate-500">{organizationId || siteId ? 'Dashboard metrics are scoped to the selected customer/site when records carry matching tenant context.' : 'Showing the MSP-wide operational view.'}</p></div><div className="flex items-center gap-2"><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${isConnected ? 'bg-emerald-100 text-emerald-700' : 'bg-white text-slate-600'}`}><span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-slate-400'}`} />{isConnected ? 'Live' : 'Offline'} telemetry</span><button onClick={load} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500"><RefreshCw size={13} className={busy ? 'animate-spin' : undefined} />Refresh</button></div></div>
      {organizationId && !hasScopedRecords && loaded && <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"><b>{scopeLabel}</b> has no devices or tickets carrying this customer/site association yet. No MSP-wide records are shown here to avoid mixing tenants.</div>}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">{[['Devices', stats.total, 'managed', Server, '/assets'], ['Online', stats.online, stats.total ? `${Math.round(stats.online / stats.total * 100)}%` : '—', Wifi, '/assets'], ['Open work', stats.active, 'tickets', Ticket, '/itsm'], ['Critical', stats.critical + stats.offline, 'needs attention', CircleAlert, '/alert-engine']].map(([label, value, detail, Icon, href], i) => <Link key={String(label)} href={String(href)} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:border-indigo-200 hover:shadow-md"><div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-500">{label}</span><Icon size={18} className={i === 3 && Number(value) ? 'text-red-500' : 'text-indigo-600'} /></div><div className="mt-2 flex items-end gap-2"><span className="text-3xl font-bold text-slate-900">{value}</span><span className="pb-1 text-xs text-slate-500">{detail}</span></div></Link>)}</div>
      <div className="grid gap-6 xl:grid-cols-[1.4fr_.8fr]"><Card title="Attention queue" icon={<AlertTriangle size={17} className="text-amber-600" />}><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[['Critical', stats.critical + stats.offline, 'red'], ['High priority', stats.high, 'amber'], ['Due today', stats.due, 'sky'], ['Overdue', stats.overdue, 'red']].map(([label, value, tone]) => <div key={label} className="rounded-xl bg-slate-50 p-4"><div className="flex items-center justify-between text-xs font-semibold text-slate-500"><span>{label}</span><span className={`h-2 w-2 rounded-full ${tone === 'amber' ? 'bg-amber-500' : tone === 'sky' ? 'bg-sky-500' : 'bg-red-500'}`} /></div><p className="mt-2 text-2xl font-bold text-slate-900">{value}</p></div>)}</div></Card><Card title="Security posture" icon={<ShieldCheck size={17} className="text-emerald-600" />}><div className="flex items-center gap-4"><div className="flex h-20 w-20 items-center justify-center rounded-full border-8 border-emerald-100 text-xl font-bold">—</div><div><p className="font-semibold">Security score</p><p className="mt-1 text-xs leading-5 text-slate-500">Populates when endpoint security integrations report posture.</p></div></div><Link href="/endpoint-security" className="mt-4 inline-flex text-xs font-semibold text-indigo-600">Open Endpoint Security →</Link></Card></div>
      <div className="grid gap-6 xl:grid-cols-2"><Card title="Device health" icon={<Monitor size={17} className="text-indigo-600" />}><div className="mb-4 flex gap-2"><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-700">{stats.online} online</span><span className="rounded-full bg-red-50 px-3 py-1 text-xs text-red-700">{stats.offline} offline</span></div><div className="space-y-2">{scopedDevices.slice(0, 8).map((d) => { const online = d.online === true || String(d.status).toLowerCase() === 'online'; return <div key={String(d.id)} className="flex items-center justify-between rounded-xl border border-slate-100 p-3"><span className="flex items-center gap-3 text-sm font-medium"><span className={`h-2 w-2 rounded-full ${online ? 'bg-emerald-500' : 'bg-red-500'}`} />{d.hostname || d.name || d.id}</span><span className="text-xs text-slate-500">{d.status || (online ? 'online' : 'offline')}</span></div>; })}</div></Card><Card title="Ticket workload" icon={<Activity size={17} className="text-indigo-600" />}><div className="space-y-4">{[['Open', stats.open], ['Pending', stats.pending], ['Due today', stats.due], ['Overdue', stats.overdue]].map(([label, value]) => <div key={label}><div className="mb-1 flex justify-between text-xs"><span className="text-slate-600">{label}</span><b>{value}</b></div><div className="h-2 rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${stats.active ? Math.min(100, Number(value) / stats.active * 100) : 0}%` }} /></div></div>)}</div></Card></div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-3"><CheckCircle2 className="text-emerald-500" size={19} /><div><p className="text-sm font-semibold">Workspace isolation</p><p className="text-xs text-slate-500">Changing the customer or site selector changes this dashboard scope. Records without tenant context are intentionally excluded from customer views.</p></div></div></div>
    </div>
  </ModuleShell>;
}
