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

function formatSeen(iso?: string | null) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function metric(n?: number | null) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  return Math.round(Number(n)) + '%';
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<StatusFilter>('all');
  const [selected, setSelected] = useState<Device | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const payload = await listDevicesDetailed();
      setDevices(payload.devices || []);
      setCounts(payload.counts || {});
    } catch (e: any) {
      setError(e?.message || 'Failed to load devices');
      setDevices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = window.setInterval(load, 15000);
    return () => window.clearInterval(t);
  }, [load]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    return devices.filter((d) => {
      const s = (d.status || 'unknown').toLowerCase();
      if (status !== 'all' && s !== status) return false;
      if (!query) return true;
      const hay = [d.hostname, d.name, d.id, d.platform, d.ip_address, d.agent_version]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(query);
    });
  }, [devices, q, status]);

  const summary = [
    { key: 'all', label: 'Total', value: devices.length },
    { key: 'online', label: 'Online', value: counts.online || 0 },
    { key: 'offline', label: 'Offline', value: counts.offline || 0 },
    { key: 'overdue', label: 'Overdue', value: counts.overdue || 0 },
  ] as const;

  return (
    <ModuleShell title="Devices" subtitle="Enrolled agents and endpoints — online, offline, overdue">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {summary.map((tile) => (
            <button
              key={tile.key}
              type="button"
              onClick={() => setStatus(tile.key as StatusFilter)}
              className={
                'rounded-2xl border px-4 py-3 text-left transition ' +
                (status === tile.key
                  ? 'border-indigo-300 bg-indigo-50 shadow-sm'
                  : 'border-slate-200 bg-white hover:bg-slate-50')
              }
            >
              <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{tile.label}</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{tile.value}</p>
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search hostname, IP, platform, agent…"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-indigo-300 focus:bg-white"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {(['all', 'online', 'offline', 'overdue'] as StatusFilter[]).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatus(s)}
                className={
                  'rounded-full border px-3 py-1.5 text-xs font-medium capitalize ' +
                  (status === s
                    ? 'border-indigo-300 bg-indigo-50 text-indigo-800'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50')
                }
              >
                {s}
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setLoading(true);
                load();
              }}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
            <Link
              href="/agents"
              className="inline-flex items-center gap-1.5 rounded-full bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
            >
              Install agent
            </Link>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Device</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Platform</th>
                  <th className="px-4 py-3 font-medium">IP</th>
                  <th className="px-4 py-3 font-medium">Last seen</th>
                  <th className="px-4 py-3 font-medium">Version</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && devices.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                      Loading devices…
                    </td>
                  </tr>
                )}
                {!loading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                      No devices match. Enroll an agent from{' '}
                      <Link href="/agents" className="font-medium text-indigo-600 hover:underline">
                        Download Agent
                      </Link>
                      .
                    </td>
                  </tr>
                )}
                {filtered.map((d) => {
                  const meta = statusMeta(d.status);
                  return (
                    <tr
                      key={d.id || d.hostname}
                      className="cursor-pointer border-b border-slate-50 hover:bg-slate-50/80"
                      onClick={() => setSelected(d)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                            <Monitor size={16} />
                          </span>
                          <div>
                            <div className="font-medium text-slate-900">{d.hostname || d.name || 'Unknown'}</div>
                            <div className="font-mono text-[11px] text-slate-400">{(d.id || '').slice(0, 8)}…</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ' +
                            meta.className
                          }
                        >
                          <span className={'h-1.5 w-1.5 rounded-full ' + meta.dot} />
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{d.platform || '—'}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-600">{d.ip_address || '—'}</td>
                      <td className="px-4 py-3 text-slate-600">{formatSeen(d.last_seen)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">{d.agent_version || '—'}</td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="flex gap-1">
                          <Link
                            href="/remote"
                            className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
                            title="Remote access"
                          >
                            <ScreenShare size={14} />
                          </Link>
                          <Link
                            href="/commands"
                            className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
                            title="Commands"
                          >
                            <Terminal size={14} />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30" onClick={() => setSelected(null)}>
          <aside
            className="flex h-full w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Device</p>
                <h2 className="text-lg font-semibold text-slate-900">{selected.hostname || selected.name}</h2>
                <p className="mt-0.5 font-mono text-[11px] text-slate-400">{selected.id}</p>
              </div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={18} />
              </button>
            </header>

            <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
              <div>
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

              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Actions</h3>
                <div className="flex flex-col gap-2">
                  <Link
                    href="/remote"
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
