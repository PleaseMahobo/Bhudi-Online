'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Monitor,
  RefreshCw,
  Search,
  ScreenShare,
  Terminal,
  X,
  Wifi,
  WifiOff,
  AlertTriangle,
  HelpCircle,
  Plus,
  Ticket,
} from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import DeviceMetricsChart from '@/shared/components/DeviceMetricsChart';
import { listDevicesDetailed, type Device } from '@/lib/devices';

type StatusFilter = 'all' | 'online' | 'offline' | 'overdue' | 'unknown';
type TypeFilter = 'all' | 'server' | 'workstation' | 'network' | 'esxi';

function statusMeta(status?: string) {
  const s = (status || 'unknown').toLowerCase();
  if (s === 'online')
    return {
      label: 'Online',
      className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      dot: 'bg-emerald-500',
      Icon: Wifi,
    };
  if (s === 'overdue')
    return {
      label: 'Overdue',
      className: 'bg-amber-50 text-amber-900 border-amber-200',
      dot: 'bg-amber-500',
      Icon: AlertTriangle,
    };
  if (s === 'offline')
    return {
      label: 'Offline',
      className: 'bg-slate-100 text-slate-700 border-slate-200',
      dot: 'bg-slate-400',
      Icon: WifiOff,
    };
  return {
    label: 'Unknown',
    className: 'bg-slate-50 text-slate-600 border-slate-200',
    dot: 'bg-slate-300',
    Icon: HelpCircle,
  };
}

function formatSeen(v?: string | null) {
  if (!v) return '—';
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleString();
}

function metric(v?: number | null) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `${Number(v).toFixed(0)}%`;
}

function deviceClass(d: Device): TypeFilter {
  const hay = [d.platform, d.hostname, d.name, (d as any).device_type, (d as any).type]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  if (/\besxi\b|hypervisor|vcenter|vmware/.test(hay)) return 'esxi';
  if (/\bserver\b|windows server|linux server|datacenter/.test(hay)) return 'server';
  if (/\bswitch\b|\brouter\b|\bfirewall\b|\bap\b|network/.test(hay)) return 'network';
  return 'workstation';
}

function deviceTypeLabel(d: Device): string {
  const explicit = (d as any).device_type || (d as any).type;
  if (explicit) return String(explicit);
  const cls = deviceClass(d);
  if (cls === 'server') return 'Server';
  if (cls === 'network') return 'Network';
  if (cls === 'esxi') return 'ESXi';
  const p = (d.platform || '').toLowerCase();
  if (p.includes('mac') || p.includes('darwin')) return 'Laptop';
  if (p.includes('linux')) return 'Workstation';
  return 'Laptop';
}

function osLabel(d: Device): string {
  return (d as any).os_name || d.platform || '—';
}

function osVersion(d: Device): string {
  return (d as any).os_version || (d as any).windows_version || (d as any).display_version || '—';
}

function lastUser(d: Device): string {
  return (d as any).last_user || (d as any).logged_in_user || (d as any).username || '—';
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const rows = await listDevicesDetailed();
      const list = Array.isArray(rows)
        ? rows
        : Array.isArray((rows as any)?.devices)
          ? (rows as any).devices
          : [];
      setDevices(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load devices');
      setDevices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 15000);
    return () => clearInterval(id);
  }, [load]);

  const typeCounts = useMemo(() => {
    const c = { all: devices.length, server: 0, workstation: 0, network: 0, esxi: 0 };
    for (const d of devices) {
      const cls = deviceClass(d);
      c[cls] += 1;
    }
    return c;
  }, [devices]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    return devices.filter((d) => {
      const status = (d.status || 'unknown').toLowerCase();
      if (filter !== 'all' && status !== filter) return false;
      if (typeFilter !== 'all' && deviceClass(d) !== typeFilter) return false;
      if (!query) return true;
      const hay = [
        d.hostname,
        d.name,
        d.ip_address,
        d.agent_id,
        d.id,
        d.platform,
        lastUser(d),
        osLabel(d),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(query);
    });
  }, [devices, filter, typeFilter, q]);

  const selected = useMemo(
    () => devices.find((d) => String(d.id) === String(selectedId)) || null,
    [devices, selectedId]
  );

  const counts = useMemo(() => {
    const c = { all: devices.length, online: 0, offline: 0, overdue: 0, unknown: 0 };
    for (const d of devices) {
      const s = (d.status || 'unknown').toLowerCase();
      if (s in c) (c as any)[s] += 1;
      else c.unknown += 1;
    }
    return c;
  }, [devices]);

  return (
    <ModuleShell
      title="Devices"
      subtitle="Live endpoints from agent heartbeats. Select a device for metrics and actions."
      breadcrumbs={[
        { label: 'Sites', href: '/msp' },
        { label: 'All Sites', href: '/msp' },
        { label: 'Devices' },
      ]}
      actions={
        <>
          <Link
            href="/agents"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Plus size={16} />
            Add Device
          </Link>
          <Link
            href="/itsm"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            <Ticket size={16} />
            Create Ticket
          </Link>
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </>
      }
    >
      <div className="mb-4 flex flex-wrap gap-2">
        {(
          [
            ['all', 'Total', typeCounts.all],
            ['server', 'Server', typeCounts.server],
            ['workstation', 'Workstation', typeCounts.workstation],
            ['network', 'Network', typeCounts.network],
            ['esxi', 'ESXi', typeCounts.esxi],
          ] as const
        ).map(([key, label, count]) => {
          const active = typeFilter === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => setTypeFilter(key)}
              className={
                'inline-flex items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-medium transition ' +
                (active
                  ? 'border-indigo-300 bg-indigo-50 text-indigo-800'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50')
              }
            >
              {label}
              <span
                className={
                  'rounded-md px-1.5 py-0.5 text-xs font-semibold tabular-nums ' +
                  (active ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500')
                }
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {(['all', 'online', 'offline', 'overdue', 'unknown'] as StatusFilter[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={
              'rounded-full border px-3 py-1 text-xs font-medium capitalize ' +
              (filter === key
                ? 'border-indigo-200 bg-indigo-50 text-indigo-800'
                : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50')
            }
          >
            {key} ({(counts as any)[key] ?? 0})
          </button>
        ))}
        <div className="relative ml-auto min-w-[200px] max-w-sm flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search hostname, user, OS, IP…"
            className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              All Managed Devices
              <span className="ml-2 font-normal text-slate-400">({filtered.length})</span>
            </h2>
            <p className="text-xs text-slate-500">
              Filtered by:{' '}
              {typeFilter === 'all' && filter === 'all'
                ? 'Unfiltered'
                : [typeFilter !== 'all' ? typeFilter : null, filter !== 'all' ? filter : null]
                    .filter(Boolean)
                    .join(' · ')}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Quick Job
            </button>
            <button
              type="button"
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
            >
              Create a Job
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                <th className="w-10 px-3 py-2.5">
                  <span className="sr-only">Status</span>
                </th>
                <th className="px-3 py-2.5">Hostname</th>
                <th className="px-3 py-2.5">Type</th>
                <th className="px-3 py-2.5">Last User</th>
                <th className="px-3 py-2.5">OS</th>
                <th className="px-3 py-2.5">OS Version</th>
                <th className="px-3 py-2.5">CPU</th>
                <th className="px-3 py-2.5">Memory</th>
                <th className="px-3 py-2.5">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {loading && devices.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-slate-500">
                    Loading devices…
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-slate-500">
                    No devices match. Install the native agent and wait for heartbeats.
                  </td>
                </tr>
              ) : (
                filtered.map((d) => {
                  const meta = statusMeta(d.status);
                  const id = String(d.id);
                  const active = selectedId === id;
                  return (
                    <tr
                      key={id}
                      onClick={() => setSelectedId(id)}
                      className={
                        'cursor-pointer border-b border-slate-50 transition hover:bg-slate-50 ' +
                        (active ? 'bg-indigo-50/60' : '')
                      }
                    >
                      <td className="px-3 py-3">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${meta.dot}`}
                          title={meta.label}
                        />
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <Monitor className="h-4 w-4 shrink-0 text-slate-400" />
                          <div className="min-w-0">
                            <Link
                              href={`/devices/${encodeURIComponent(id)}`}
                              onClick={(e) => e.stopPropagation()}
                              className="block truncate font-medium text-indigo-700 hover:underline"
                            >
                              {d.hostname || d.name || id}
                            </Link>
                            <div className="truncate text-xs text-slate-500">
                              {d.ip_address || d.agent_id || '—'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-slate-700">{deviceTypeLabel(d)}</td>
                      <td className="max-w-[10rem] truncate px-3 py-3 text-slate-600">
                        {lastUser(d)}
                      </td>
                      <td className="max-w-[12rem] truncate px-3 py-3 text-slate-700">
                        {osLabel(d)}
                      </td>
                      <td className="px-3 py-3 tabular-nums text-slate-600">{osVersion(d)}</td>
                      <td className="px-3 py-3 tabular-nums text-slate-700">
                        {metric(d.cpu_percent as number)}
                      </td>
                      <td className="px-3 py-3 tabular-nums text-slate-700">
                        {metric(d.memory_percent as number)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-slate-500">
                        {formatSeen(d.last_seen)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-40 flex justify-end bg-black/20"
          onClick={() => setSelectedId(null)}
        >
          <aside
            className="flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-slate-200 bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  {selected.hostname || selected.name || selected.id}
                </h2>
                <p className="text-xs text-slate-500">{selected.id}</p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedId(null)}
                className="rounded-lg p-2 hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-5 p-5">
              <div className="flex items-center gap-2">
                {(() => {
                  const meta = statusMeta(selected.status);
                  return (
                    <span
                      className={
                        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ' +
                        meta.className
                      }
                    >
                      <span className={'h-1.5 w-1.5 rounded-full ' + meta.dot} />
                      {meta.label}
                    </span>
                  );
                })()}
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
                  {deviceTypeLabel(selected)}
                </span>
              </div>

              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Overview
                </h3>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">Platform</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">
                      {selected.platform || '—'}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">IP address</dt>
                    <dd className="mt-0.5 font-mono text-xs font-medium text-slate-900">
                      {selected.ip_address || '—'}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">Last user</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">{lastUser(selected)}</dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">Last seen</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">
                      {formatSeen(selected.last_seen)}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">Agent version</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">
                      {selected.agent_version || '—'}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">OS version</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">{osVersion(selected)}</dd>
                  </div>
                </dl>
              </section>

              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Performance
                </h3>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    ['CPU', selected.cpu_percent],
                    ['Memory', selected.memory_percent],
                    ['Disk', selected.disk_percent],
                  ].map(([label, val]) => (
                    <div
                      key={String(label)}
                      className="rounded-xl border border-slate-100 p-3 text-center"
                    >
                      <p className="text-[11px] text-slate-500">{label}</p>
                      <p className="mt-1 text-lg font-semibold text-slate-900">
                        {metric(val as number)}
                      </p>
                    </div>
                  ))}
                </div>
              </section>

              <DeviceMetricsChart
                deviceId={String(selected.agent_id || selected.device_id || selected.id)}
                hostname={selected.hostname || selected.name}
                minutes={60}
              />

              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Actions
                </h3>
                <div className="flex flex-col gap-2">
                  <Link
                    href={`/remote?agent=${encodeURIComponent(String(selected.agent_id || selected.id))}`}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
                  >
                    <ScreenShare size={16} />
                    Remote access
                  </Link>
                  <Link
                    href="/commands"
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <Terminal size={16} />
                    Run command
                  </Link>
                </div>
              </section>
            </div>
          </aside>
        </div>
      )}
    </ModuleShell>
  );
}
