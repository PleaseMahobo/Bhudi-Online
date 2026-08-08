'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/shared/auth/AuthContext';
import ModuleShell from '@/shared/components/ModuleShell';
import { getDevices, listTickets, type ServiceTicket } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';
import {
  AlertTriangle,
  Bell,
  Check,
  Copy,
  Monitor,
  Ticket,
  Wifi,
  WifiOff,
  Activity,
  Server,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';

type DeviceRow = {
  id: string;
  hostname?: string;
  name?: string;
  status?: string;
  online?: boolean;
};

function isOpenTicket(status: string) {
  const s = (status || '').toLowerCase();
  return ['open', 'new', 'in_progress', 'in-progress', 'assigned'].includes(s);
}

function isPendingTicket(status: string) {
  const s = (status || '').toLowerCase();
  return ['pending', 'waiting', 'on_hold', 'on-hold', 'customer_pending'].includes(s);
}

function isResolvedTicket(status: string) {
  const s = (status || '').toLowerCase();
  return ['resolved', 'closed', 'done', 'cancelled'].includes(s);
}

function daysFromNow(iso?: string | null) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.floor((t - Date.now()) / 86400000);
}

function StatusPill({
  href,
  label,
  count,
  tone,
}: {
  href: string;
  label: string;
  count: number;
  tone: 'slate' | 'amber' | 'red' | 'sky' | 'emerald';
}) {
  const tones: Record<string, string> = {
    slate: 'bg-slate-100 text-slate-800 hover:bg-slate-200 border-slate-200',
    amber: 'bg-amber-50 text-amber-900 hover:bg-amber-100 border-amber-200',
    red: 'bg-red-50 text-red-800 hover:bg-red-100 border-red-200',
    sky: 'bg-sky-50 text-sky-900 hover:bg-sky-100 border-sky-200',
    emerald: 'bg-emerald-50 text-emerald-900 hover:bg-emerald-100 border-emerald-200',
  };
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${tones[tone]}`}
    >
      <span className="tabular-nums font-semibold">{count}</span>
      <span className="text-xs opacity-80">{label}</span>
    </Link>
  );
}

function Widget({
  title,
  icon,
  action,
  children,
  className = '',
}: {
  title: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}
    >
      <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          {icon}
          {title}
        </div>
        {action}
      </header>
      <div className="flex-1 p-5">{children}</div>
    </section>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const { isConnected } = useWebSocket();

  const [devices, setDevices] = useState<DeviceRow[]>([]);
  const [tickets, setTickets] = useState<ServiceTicket[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const agentStartCommand =
    "$env:BHUDI_SERVER_URL='https://bhudi-online-production.up.railway.app'; Set-Location .\\agent; pip install -r requirements.txt; python main.py";

  const load = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [deviceList, ticketList] = await Promise.all([
        getDevices().catch(() => []),
        listTickets().catch(() => [] as ServiceTicket[]),
      ]);
      setDevices(Array.isArray(deviceList) ? deviceList : []);
      setTickets(Array.isArray(ticketList) ? ticketList : []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load dashboard');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (loading || !user) return;
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [loading, user, load]);

  const ticketStats = useMemo(() => {
    let open = 0;
    let pending = 0;
    let dueToday = 0;
    let overdue = 0;
    for (const t of tickets) {
      const st = t.status || '';
      if (isResolvedTicket(st)) continue;
      if (isPendingTicket(st)) pending += 1;
      else if (isOpenTicket(st)) open += 1;
      else open += 1;

      // Prefer explicit due fields if present on payload
      const due =
        (t as any).due_at || (t as any).due_date || (t as any).sla_due_at || null;
      const d = daysFromNow(due);
      if (d === 0) dueToday += 1;
      if (d !== null && d < 0) overdue += 1;
    }
    return { open, pending, dueToday, overdue, total: tickets.length };
  }, [tickets]);

  const deviceStats = useMemo(() => {
    const total = devices.length;
    const online = devices.filter((d) => d.online === true || d.status === 'online').length;
    const offline = Math.max(0, total - online);
    return { total, online, offline };
  }, [devices]);

  // Alert proxies until a unified open-alerts API is wired: high-priority open tickets + offline devices
  const alertStats = useMemo(() => {
    const critical =
      devices.filter((d) => d.online === false || d.status === 'offline').length +
      tickets.filter(
        (t) =>
          !isResolvedTicket(t.status || '') &&
          ['critical', 'urgent', 'p1'].includes((t.priority || '').toLowerCase())
      ).length;
    const warning = tickets.filter(
      (t) =>
        !isResolvedTicket(t.status || '') &&
        ['high', 'warning', 'p2'].includes((t.priority || '').toLowerCase())
    ).length;
    return { critical, warning };
  }, [devices, tickets]);

  const recentTickets = useMemo(() => {
    return [...tickets]
      .sort((a, b) => {
        const ta = new Date((a as any).updated_at || (a as any).created_at || 0).getTime();
        const tb = new Date((b as any).updated_at || (b as any).created_at || 0).getTime();
        return tb - ta;
      })
      .slice(0, 8);
  }, [tickets]);

  const copyAgentStartCommand = async () => {
    try {
      await navigator.clipboard.writeText(agentStartCommand);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  if (loading) {
    return (
      <ModuleShell title="Dashboard">
        <div className="text-slate-500">Loading…</div>
      </ModuleShell>
    );
  }

  return (
    <ModuleShell title="Dashboard" subtitle="Attention view — tickets, alerts, and estate health">
      <div className="space-y-6">
        {/* Top bar: live status + refresh (Atera-style attention strip) */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                isConnected
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}
            >
              {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
              {isConnected ? 'Live stream connected' : 'Live stream offline'}
            </span>
            {busy && (
              <span className="text-xs text-slate-400">Refreshing…</span>
            )}
          </div>
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={14} className={busy ? 'animate-spin' : undefined} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Pinned: Ticket status (Atera pattern — click pills → filtered tickets) */}
        <Widget
          title="Ticket status"
          icon={<Ticket size={16} className="text-indigo-600" />}
          action={
            <Link
              href="/itsm"
              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-500"
            >
              Open tickets <ExternalLink size={12} />
            </Link>
          }
        >
          <div className="flex flex-wrap gap-2">
            <StatusPill href="/itsm?status=open" label="Open" count={ticketStats.open} tone="sky" />
            <StatusPill
              href="/itsm?status=pending"
              label="Pending"
              count={ticketStats.pending}
              tone="amber"
            />
            <StatusPill
              href="/itsm"
              label="Due today"
              count={ticketStats.dueToday}
              tone="slate"
            />
            <StatusPill
              href="/itsm"
              label="Overdue"
              count={ticketStats.overdue}
              tone="red"
            />
          </div>
          <p className="mt-3 text-xs text-slate-500">
            {ticketStats.total} tickets in queue · click a status to jump into ITSM
          </p>
        </Widget>

        {/* Pinned: Alert status */}
        <Widget
          title="Alert status"
          icon={<Bell size={16} className="text-amber-600" />}
          action={
            <Link
              href="/alert-engine"
              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-500"
            >
              Alert engine <ExternalLink size={12} />
            </Link>
          }
        >
          <div className="flex flex-wrap gap-2">
            <StatusPill
              href="/alert-engine"
              label="Warning"
              count={alertStats.warning}
              tone="amber"
            />
            <StatusPill
              href="/alert-engine"
              label="Critical"
              count={alertStats.critical}
              tone="red"
            />
            <StatusPill
              href="/assets"
              label="Devices offline"
              count={deviceStats.offline}
              tone="slate"
            />
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Critical combines offline devices and urgent open tickets until a unified alerts feed is
            wired.
          </p>
        </Widget>

        {/* Metric strip */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            {
              label: 'Devices',
              value: deviceStats.total,
              href: '/assets',
              icon: <Server size={16} className="text-slate-500" />,
            },
            {
              label: 'Online',
              value: deviceStats.online,
              href: '/assets',
              icon: <Monitor size={16} className="text-emerald-600" />,
            },
            {
              label: 'Offline',
              value: deviceStats.offline,
              href: '/assets',
              icon: <WifiOff size={16} className="text-red-500" />,
            },
            {
              label: 'Open tickets',
              value: ticketStats.open + ticketStats.pending,
              href: '/itsm',
              icon: <Ticket size={16} className="text-indigo-600" />,
            },
          ].map((m) => (
            <Link
              key={m.label}
              href={m.href}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">{m.label}</span>
                {m.icon}
              </div>
              <div className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{m.value}</div>
            </Link>
          ))}
        </div>

        {/* Main widget grid */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <Widget
            className="xl:col-span-2"
            title="Recent ticket activity"
            icon={<Activity size={16} className="text-indigo-600" />}
            action={
              <Link href="/itsm" className="text-xs font-medium text-indigo-600 hover:text-indigo-500">
                View all
              </Link>
            }
          >
            {recentTickets.length === 0 ? (
              <p className="text-sm text-slate-500">No tickets yet. Create one from ITSM.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {recentTickets.map((t) => (
                  <li key={t.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-900">
                        {(t as any).number ? `${(t as any).number} · ` : ''}
                        {t.title || 'Untitled ticket'}
                      </p>
                      <p className="text-xs text-slate-500">
                        {(t.status || 'unknown').replace(/_/g, ' ')} · {(t.priority || '—').toLowerCase()}
                      </p>
                    </div>
                    <Link
                      href="/itsm"
                      className="shrink-0 text-xs font-medium text-indigo-600 hover:text-indigo-500"
                    >
                      Open
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Widget>

          <Widget
            title="Attention"
            icon={<AlertTriangle size={16} className="text-amber-600" />}
          >
            <ul className="space-y-3 text-sm">
              <li className="flex items-start justify-between gap-2 rounded-lg bg-red-50 px-3 py-2 text-red-900">
                <span>Critical / offline signals</span>
                <span className="font-semibold tabular-nums">{alertStats.critical}</span>
              </li>
              <li className="flex items-start justify-between gap-2 rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
                <span>High-priority tickets</span>
                <span className="font-semibold tabular-nums">{alertStats.warning}</span>
              </li>
              <li className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-slate-800">
                <span>Devices offline</span>
                <span className="font-semibold tabular-nums">{deviceStats.offline}</span>
              </li>
            </ul>
            <Link
              href="/endpoint-security"
              className="mt-4 inline-flex text-xs font-medium text-indigo-600 hover:text-indigo-500"
            >
              Review endpoint security →
            </Link>
          </Widget>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <Widget
            className="xl:col-span-2"
            title="Devices"
            icon={<Monitor size={16} className="text-indigo-600" />}
            action={
              <Link href="/assets" className="text-xs font-medium text-indigo-600 hover:text-indigo-500">
                Manage assets
              </Link>
            }
          >
            {devices.length === 0 ? (
              <p className="text-sm text-slate-500">
                No devices reporting yet. Deploy an agent with the command on the right.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[480px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-500">
                      <th className="pb-2 pr-3 font-medium">Device</th>
                      <th className="pb-2 pr-3 font-medium">Status</th>
                      <th className="pb-2 font-medium">Availability</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {devices.slice(0, 10).map((d) => {
                      const online = d.online === true || d.status === 'online';
                      return (
                        <tr key={d.id} className="text-slate-800">
                          <td className="py-2.5 pr-3 font-medium">
                            {d.hostname || d.name || d.id.slice(0, 8)}
                          </td>
                          <td className="py-2.5 pr-3 text-slate-600">{d.status || '—'}</td>
                          <td className="py-2.5">
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                                online
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : 'bg-slate-100 text-slate-600'
                              }`}
                            >
                              {online ? 'Online' : 'Offline'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {devices.length > 10 && (
                  <p className="mt-3 text-xs text-slate-500">
                    Showing 10 of {devices.length}.{' '}
                    <Link href="/assets" className="text-indigo-600 hover:text-indigo-500">
                      View all
                    </Link>
                  </p>
                )}
              </div>
            )}
          </Widget>

          <Widget title="Deploy agent" icon={<Server size={16} className="text-indigo-600" />}>
            <p className="text-xs leading-relaxed text-slate-600">
              Run on a Windows host to register with Bhudi. PowerShell example:
            </p>
            <pre className="mt-3 max-h-40 overflow-auto rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-200">
              {agentStartCommand}
            </pre>
            <button
              type="button"
              onClick={copyAgentStartCommand}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy command'}
            </button>
          </Widget>
        </div>
      </div>
    </ModuleShell>
  );
}
