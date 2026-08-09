'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState, type ComponentType } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  Download,
  Monitor,
  RefreshCw,
  Server,
  ShieldCheck,
  Ticket,
  Wifi,
} from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import AgentInstallerPanel from '@/shared/components/AgentInstallerPanel';
import { useAuth } from '@/shared/auth/AuthContext';
import { useWorkspace } from '@/shared/context/WorkspaceContext';
import { getDevices, listTickets, type ServiceTicket } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';

type Row = Record<string, any>;
type StatCard = {
  label: string;
  value: string | number;
  detail: string;
  Icon: ComponentType<{ size?: number; className?: string }>;
  tone: string;
};

const resolved = (s?: string) =>
  ['resolved', 'closed', 'done', 'cancelled'].includes((s || '').toLowerCase());
const pending = (s?: string) =>
  ['pending', 'waiting', 'on_hold', 'on-hold', 'customer_pending'].includes((s || '').toLowerCase());
const days = (v?: string | null) => {
  if (!v) return null;
  const t = new Date(v).getTime();
  return Number.isNaN(t) ? null : Math.floor((t - Date.now()) / 86400000);
};

function matchesScope(
  row: Row,
  organizationId: string | null,
  siteId: string | null,
  tenantId?: string
) {
  if (!organizationId && !siteId) return true;
  const organizationCandidates = [row.organization_id, row.organizationId].filter(Boolean).map(String);
  const siteCandidates = [row.site_id, row.siteId].filter(Boolean).map(String);
  const tenantCandidates = [row.tenant_id, row.tenantId].filter(Boolean).map(String);
  if (siteId) return siteCandidates.includes(String(siteId));
  return (
    organizationCandidates.includes(String(organizationId)) ||
    (!!tenantId && tenantCandidates.includes(String(tenantId)))
  );
}

function Card({
  title,
  children,
  icon,
}: {
  title: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-sm font-semibold text-slate-900">
        {icon}
        {title}
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
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
      const [d, t] = await Promise.all([
        getDevices().catch(() => []),
        listTickets().catch(() => [] as ServiceTicket[]),
      ]);
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
    () => devices.filter((d) => matchesScope(d, organizationId, siteId, user?.tenant_id)),
    [devices, organizationId, siteId, user?.tenant_id]
  );
  const scopedTickets = useMemo(
    () => tickets.filter((t) => matchesScope(t as Row, organizationId, siteId, user?.tenant_id)),
    [tickets, organizationId, siteId, user?.tenant_id]
  );

  const online = scopedDevices.filter((d) =>
    ['online', 'active', 'connected'].includes(String(d.status || '').toLowerCase())
  ).length;
  const offline = Math.max(0, scopedDevices.length - online);

  const stats = useMemo(() => {
    const open = scopedTickets.filter((t) => !resolved(t.status)).length;
    const pend = scopedTickets.filter((t) => pending(t.status)).length;
    const due = scopedTickets.filter((t) => {
      const d = days(t.due_date || (t as any).due_at);
      return d !== null && d === 0 && !resolved(t.status);
    }).length;
    const overdue = scopedTickets.filter((t) => {
      const d = days(t.due_date || (t as any).due_at);
      return d !== null && d < 0 && !resolved(t.status);
    }).length;
    return { open, pending: pend, due, overdue, active: open || 1 };
  }, [scopedTickets]);

  const cards: StatCard[] = [
    {
      label: 'Devices online',
      value: online,
      detail: `${scopedDevices.length} total in scope`,
      Icon: Wifi,
      tone: 'text-emerald-600',
    },
    {
      label: 'Devices offline',
      value: offline,
      detail: 'Not reporting',
      Icon: Monitor,
      tone: 'text-amber-600',
    },
    {
      label: 'Open tickets',
      value: stats.open,
      detail: `${stats.pending} pending`,
      Icon: Ticket,
      tone: 'text-indigo-600',
    },
    {
      label: 'Overdue',
      value: stats.overdue,
      detail: `${stats.due} due today`,
      Icon: AlertTriangle,
      tone: 'text-red-600',
    },
  ];

  return (
    <ModuleShell>
      <div className="space-y-6 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              {organization?.name || site?.name || 'Executive dashboard'}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {workspaceLoading ? 'Loading workspace…' : 'Live operations overview'}
              {isConnected ? ' · Live' : ''}
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={15} className={busy ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Always-visible agent download entry */}
        <Link
          href="/agents"
          className="flex flex-col gap-3 rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50 to-white p-5 shadow-sm transition hover:border-indigo-300 hover:shadow-md sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <Download size={20} />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-900">Download agent</p>
              <p className="mt-0.5 text-xs text-slate-600">
                Windows MSI/EXE · Linux · macOS — native install, no Python required
              </p>
            </div>
          </div>
          <span className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">
            Open installer
          </span>
        </Link>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <CircleAlert size={16} />
            {error}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map((c) => (
            <div key={c.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-slate-500">{c.label}</p>
                <c.Icon size={18} className={c.tone} />
              </div>
              <p className="mt-2 text-2xl font-bold text-slate-900">{c.value}</p>
              <p className="mt-1 text-xs text-slate-500">{c.detail}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Devices in scope" icon={<Server size={17} className="text-indigo-600" />}>
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {scopedDevices.slice(0, 12).map((d) => {
                const on = ['online', 'active', 'connected'].includes(
                  String(d.status || '').toLowerCase()
                );
                return (
                  <div
                    key={String(d.id || d.hostname)}
                    className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2"
                  >
                    <span className="flex items-center gap-2 text-sm font-medium text-slate-800">
                      <span
                        className={`h-2 w-2 rounded-full ${
                          on ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                      />
                      {d.hostname || d.name || d.id}
                    </span>
                    <span className="text-xs text-slate-500">
                      {d.status || (on ? 'online' : 'offline')}
                    </span>
                  </div>
                );
              })}
              {scopedDevices.length === 0 && (
                <p className="text-sm text-slate-500">
                  No devices yet.{' '}
                  <Link href="/agents" className="font-medium text-indigo-600 hover:underline">
                    Download an agent
                  </Link>{' '}
                  to enroll the first endpoint.
                </p>
              )}
            </div>
          </Card>

          <Card title="Ticket workload" icon={<Activity size={17} className="text-indigo-600" />}>
            <div className="space-y-4">
              {(
                [
                  ['Open', stats.open],
                  ['Pending', stats.pending],
                  ['Due today', stats.due],
                  ['Overdue', stats.overdue],
                ] as const
              ).map(([label, value]) => (
                <div key={label}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-slate-600">{label}</span>
                    <b>{value}</b>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-indigo-500"
                      style={{
                        width: `${stats.active ? Math.min(100, (Number(value) / stats.active) * 100) : 0}%`,
                      }}
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
                Changing the customer or site selector changes this dashboard scope. Records without
                tenant context are intentionally excluded from customer views.
              </p>
            </div>
          </div>
        </div>
      </div>
    </ModuleShell>
  );
}
