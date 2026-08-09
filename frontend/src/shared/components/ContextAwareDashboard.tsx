'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState, type ComponentType } from 'react';
import { Activity, AlertTriangle, CheckCircle2, CircleAlert, Monitor, RefreshCw, Server, ShieldCheck, Ticket, Wifi } from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import AgentInstallerPanel from '@/shared/components/AgentInstallerPanel';
import { useAuth } from '@/shared/auth/AuthContext';
import { useWorkspace } from '@/shared/context/WorkspaceContext';
import { getDevices, listTickets, type ServiceTicket } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';

type Row = Record<string, any>;
type StatCard = { label: string; value: string | number; detail: string; Icon: ComponentType<{ size?: number; className?: string }>; href: string };
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
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [d, t] = await Promise.all([getDevices().catch(() => []), listTickets().catch(() => [] as ServiceTicket[])]);
      setDevices(Array.isArray(d) ? d : []);
      setTickets(Array.isArray(t) ? t : []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load dashboard');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !user) return;
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [authLoading, user, load]);

  const scopedDevices = useMemo(
    () => devices.filter((d) => matchesScope(d, organizationId, siteId, (organization as any)?.tenant_id)),
    [devices, organizationId, siteId, organization]
  );
  const scopedTickets = useMemo(
    () => tickets.filter((t) => matchesScope(t as any, organizationId, siteId, (organization as any)?.tenant_id)),
    [tickets, organizationId, siteId, organization]
  );

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

  const statCards: StatCard[] = [
    { label: 'Devices', value: stats.total, detail: 'managed', Icon: Server, href: '/assets' },
    { label: 'Online', value: stats.online, detail: stats.total ? `${Math.round(stats.online / stats.total * 100)}%` : '—', Icon: Wifi, href: '/assets' },
    { label: 'Open work', value: stats.active, detail: 'tickets', Icon: Ticket, href: '/itsm' },
    { label: 'Critical', value: stats.critical + stats.offline, detail: 'needs attention', Icon: CircleAlert, href: '/alert-engine' },
  ];

  return (
    <ModuleShell title="Operations Center" subtitle="Context-aware operational view across devices, tickets and alerts">
      <div className="space-y-6">
        <div className="flex flex-col gap-3 rounded-2xl border border-indigo-100 bg-indigo-50/70 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-500">Current scope</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">{scopeLabel}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {organizationId || siteId
                ? 'Dashboard metrics are scoped to the selected customer/site when records carry tenant metadata.'
                : 'Showing all accessible devices and tickets.'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${isConnected ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white text-slate-600'}`}>
              <Wifi size={12} />
              {isConnected ? 'Live' : 'Offline'}
            </span>
            <button type="button" onClick={load} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
              <RefreshCw size={13} className={busy ? 'animate-spin' : undefined} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {statCards.map(({ label, value, detail, Icon, href }) => (
            <Link key={label} href={href} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-200 hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">{label}</span>
                <Icon size={16} className="text-slate-400" />
              </div>
              <div className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{value}</div>
              <div className="mt-0.5 text-[11px] text-slate-400">{detail}</div>
            </Link>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card title="Attention" icon={<AlertTriangle size={17} className="text-amber-600" />}>
            <ul className="space-y-2 text-sm">
              <li className="flex justify-between rounded-lg bg-red-50 px-3 py-2 text-red-900">
                <span>Critical tickets</span>
                <b>{stats.critical}</b>
              </li>
              <li className="flex justify-between rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
                <span>High priority</span>
                <b>{stats.high}</b>
              </li>
              <li className="flex justify-between rounded-lg bg-slate-50 px-3 py-2 text-slate-800">
                <span>Offline devices</span>
                <b>{stats.offline}</b>
              </li>
            </ul>
            <Link href="/alert-engine" className="mt-4 inline-flex text-xs font-semibold text-indigo-600">
              Open Alert Engine →
            </Link>
          </Card>

          <Card title="Ticket status" icon={<Ticket size={17} className="text-indigo-600" />}>
            <div className="flex flex-wrap gap-2">
              <Link href="/itsm" className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-900">
                {stats.open} open
              </Link>
              <Link href="/itsm" className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-900">
                {stats.pending} pending
              </Link>
              <Link href="/itsm" className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-800">
                {stats.due} due today
              </Link>
              <Link href="/itsm" className="rounded-full bg-red-50 px-3 py-1.5 text-xs font-medium text-red-800">
                {stats.overdue} overdue
              </Link>
            </div>
          </Card>

          <Card title="Security posture" icon={<ShieldCheck size={17} className="text-emerald-600" />}>
            <div className="flex items-center gap-4">
              <div className="flex h-20 w-20 items-center justify-center rounded-full border-8 border-emerald-100 text-xl font-bold">—</div>
              <div>
                <p className="font-semibold">Security score</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Populates when endpoint security integrations report posture.
                </p>
              </div>
            </div>
            <Link href="/endpoint-security" className="mt-4 inline-flex text-xs font-semibold text-indigo-600">
              Open Endpoint Security →
            </Link>
          </Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Card title="Device health" icon={<Monitor size={17} className="text-indigo-600" />}>
            <div className="mb-4 flex gap-2">
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-700">{stats.online} online</span>
              <span className="rounded-full bg-red-50 px-3 py-1 text-xs text-red-700">{stats.offline} offline</span>
            </div>
            <div className="space-y-2">
              {scopedDevices.slice(0, 8).map((d) => {
                const online = d.online === true || String(d.status).toLowerCase() === 'online';
                return (
                  <div key={String(d.id)} className="flex items-center justify-between rounded-xl border border-slate-100 p-3">
                    <span className="flex items-center gap-3 text-sm font-medium">
                      <span className={`h-2 w-2 rounded-full ${online ? 'bg-emerald-500' : 'bg-red-500'}`} />
                      {d.hostname || d.name || d.id}
                    </span>
                    <span className="text-xs text-slate-500">{d.status || (online ? 'online' : 'offline')}</span>
                  </div>
                );
              })}
              {scopedDevices.length === 0 && (
                <p className="text-sm text-slate-500">No devices in this scope yet. Install an agent below.</p>
              )}
            </div>
          </Card>

          <Card title="Ticket workload" icon={<Activity size={17} className="text-indigo-600" />}>
            <div className="space-y-4">
              {[['Open', stats.open], ['Pending', stats.pending], ['Due today', stats.due], ['Overdue', stats.overdue]].map(([label, value]) => (
                <div key={String(label)}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-slate-600">{label}</span>
                    <b>{value}</b>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-indigo-500"
                      style={{ width: `${stats.active ? Math.min(100, (Number(value) / stats.active) * 100) : 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <AgentInstallerPanel />

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="text-emerald-500" size={19} />
            <div>
              <p className="text-sm font-semibold">Workspace isolation</p>
              <p className="text-xs text-slate-500">
                Changing the customer or site selector changes this dashboard scope. Records without tenant context are
                intentionally excluded from customer views.
              </p>
            </div>
          </div>
        </div>
      </div>
    </ModuleShell>
  );
}
