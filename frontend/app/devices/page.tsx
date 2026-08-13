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
} from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import DeviceMetricsChart from '@/shared/components/DeviceMetricsChart';
import { listDevicesDetailed, type Device } from '@/lib/devices';

type StatusFilter = 'all' | 'online' | 'offline' | 'overdue' | 'unknown';

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

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const rows = await listDevicesDetailed();
      setDevices(Array.isArray(rows) ? rows : []);
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

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    return devices.filter((d) => {
      const status = (d.status || 'unknown').toLowerCase();
      if (filter !== 'all' && status !== filter) return false;
      if (!query) return true;
      const hay = [d.hostname, d.name, d.ip_address, d.agent_id, d.id, d.platform]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(query);
    });
  }, [devices, filter, q]);

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
    <ModuleShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Devices</h1>
          <p className="mt-1 text-sm text-slate-500">
            Live endpoints from agent heartbeats. Select a device for metrics graphs.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
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
        <div className="relative ml-auto min-w-[200px] flex-1 max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search hostname, IP, id…"
            className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Device</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">CPU</th>
              <th className="px-4 py-3 font-medium">Memory</th>
              <th className="px-4 py-3 font-medium">Last seen</th>
            </tr>
          </thead>
          <tbody>
            {loading && devices.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                  Loading devices…
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                  No devices match. Install the native agent and wait for heartbeats.
                </td>
              </tr>
            ) : (
              filtered.map((d) => {
                const meta = statusMeta(d.status);
                const id = String(d.id);
                return (
                  <tr
                    key={id}
                    onClick={() => setSelectedId(id)}
                    className={
                      'cursor-pointer border-b border-slate-50 hover:bg-slate-50 ' +
                      (selectedId === id ? 'bg-indigo-50/50' : '')
                    }
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Monitor className="h-4 w-4 text-slate-400" />
                        <div>
                          <div className="font-medium text-slate-900">{d.hostname || d.name || id}</div>
                          <div className="text-xs text-slate-500">{d.platform || '—'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ' +
                          meta.className
                        }
                      >
                        <span className={'h-1.5 w-1.5 rounded-full ' + meta.dot} />
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 tabular-nums">{metric(d.cpu_percent as number)}</td>
                    <td className="px-4 py-3 tabular-nums">{metric(d.memory_percent as number)}</td>
                    <td className="px-4 py-3 text-slate-600">{formatSeen(d.last_seen)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 z-40 flex justify-end bg-black/20" onClick={() => setSelectedId(null)}>
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
              <button type="button" onClick={() => setSelectedId(null)} className="rounded-lg p-2 hover:bg-slate-100">
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
              </div>

              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Overview</h3>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">Platform</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">{selected.platform || '—'}</dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">IP address</dt>
                    <dd className="mt-0.5 font-mono text-xs font-medium text-slate-900">
                      {selected.ip_address || '—'}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">Last seen</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">{formatSeen(selected.last_seen)}</dd>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <dt className="text-[11px] text-slate-500">Agent version</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">{selected.agent_version || '—'}</dd>
                  </div>
                </dl>
              </section>

              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Performance</h3>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    ['CPU', selected.cpu_percent],
                    ['Memory', selected.memory_percent],
                    ['Disk', selected.disk_percent],
                  ].map(([label, val]) => (
                    <div key={String(label)} className="rounded-xl border border-slate-100 p-3 text-center">
                      <p className="text-[11px] text-slate-500">{label}</p>
                      <p className="mt-1 text-lg font-semibold text-slate-900">{metric(val as number)}</p>
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
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Actions</h3>
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
