'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  Monitor,
  RefreshCw,
  ScreenShare,
  Terminal,
  Package,
  Cpu,
} from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import DeviceMetricsChart from '@/shared/components/DeviceMetricsChart';
import {
  getDevice,
  requestInventory,
  waitForCommand,
  remoteDeepLink,
  type Device,
} from '@/lib/devices';

type Tab = 'overview' | 'processes' | 'software' | 'remote';

function statusClass(s?: string) {
  const v = (s || '').toLowerCase();
  if (v === 'online') return 'bg-emerald-50 text-emerald-800 border-emerald-200';
  if (v === 'overdue') return 'bg-amber-50 text-amber-900 border-amber-200';
  if (v === 'offline') return 'bg-slate-100 text-slate-700 border-slate-200';
  return 'bg-slate-50 text-slate-600 border-slate-200';
}

export default function DeviceDetailPage() {
  const params = useParams();
  const search = useSearchParams();
  const router = useRouter();
  const id = String(params?.id || '');
  const initialTab = (search.get('tab') as Tab) || 'overview';

  const [tab, setTab] = useState<Tab>(initialTab);
  const [device, setDevice] = useState<Device | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [invBusy, setInvBusy] = useState(false);
  const [processOut, setProcessOut] = useState('');
  const [softwareOut, setSoftwareOut] = useState('');
  const [invError, setInvError] = useState('');

  const load = useCallback(async () => {
    if (!id) return;
    setError(null);
    try {
      const d = await getDevice(id);
      setDevice(d);
    } catch (e: any) {
      setError(e?.message || 'Device not found');
      setDevice(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const t = search.get('tab') as Tab;
    if (t && ['overview', 'processes', 'software', 'remote'].includes(t)) setTab(t);
  }, [search]);

  async function runInventory(kind: 'processes' | 'software') {
    if (!device?.id) return;
    setInvBusy(true);
    setInvError('');
    try {
      const queued = await requestInventory(device.id, kind);
      const result = await waitForCommand(device.id, queued.command_id);
      const text = (result.stdout || result.stderr || '').trim() || '(empty output)';
      if (kind === 'processes') setProcessOut(text);
      else setSoftwareOut(text);
    } catch (e: any) {
      setInvError(e?.message || 'Inventory failed — is the agent online?');
    } finally {
      setInvBusy(false);
    }
  }

  const agentId = device?.agent_id || device?.device_id || device?.id || '';

  const tabs: { key: Tab; label: string; icon: typeof Monitor }[] = [
    { key: 'overview', label: 'Overview', icon: Monitor },
    { key: 'processes', label: 'Processes', icon: Cpu },
    { key: 'software', label: 'Software', icon: Package },
    { key: 'remote', label: 'Remote', icon: ScreenShare },
  ];

  return (
    <ModuleShell
      title={device?.hostname || device?.name || 'Device'}
      subtitle={device ? 'Agent ' + device.id : 'Device detail'}
    >
      <div className="mb-4">
        <button
          type="button"
          onClick={() => router.push('/devices')}
          className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-indigo-600"
        >
          <ArrowLeft size={16} />
          All devices
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="animate-spin" size={16} /> Loading…
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {device && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <span className={'rounded-full border px-2.5 py-1 text-xs font-medium ' + statusClass(device.status)}>
              {(device.status || 'unknown').toString()}
            </span>
            <span className="text-sm text-slate-600">{device.platform || '—'}</span>
            <span className="font-mono text-xs text-slate-500">{device.ip_address || 'no IP'}</span>
            <div className="ml-auto flex gap-2">
              <Link
                href={remoteDeepLink(agentId, 'desktop')}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
              >
                <ScreenShare size={14} /> Remote desktop
              </Link>
              <Link
                href={remoteDeepLink(agentId, 'terminal')}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <Terminal size={14} /> Terminal
              </Link>
              <button
                type="button"
                onClick={() => {
                  setLoading(true);
                  load();
                }}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50"
              >
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-1 border-b border-slate-200">
            {tabs.map((t) => {
              const Icon = t.icon;
              const active = tab === t.key;
              return (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => {
                    setTab(t.key);
                    router.replace('/devices/' + encodeURIComponent(id) + '?tab=' + t.key, {
                      scroll: false,
                    });
                  }}
                  className={
                    'inline-flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-sm font-medium transition ' +
                    (active
                      ? 'border-indigo-600 text-indigo-700'
                      : 'border-transparent text-slate-500 hover:text-slate-800')
                  }
                >
                  <Icon size={14} />
                  {t.label}
                </button>
              );
            })}
          </div>

          {tab === 'overview' && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ['Hostname', device.hostname || device.name],
                  ['Last seen', device.last_seen || '—'],
                  ['Agent version', device.agent_version || '—'],
                  ['Source', device.source || '—'],
                  ['CPU', device.cpu_percent != null ? Math.round(device.cpu_percent) + '%' : '—'],
                  ['Memory', device.memory_percent != null ? Math.round(device.memory_percent) + '%' : '—'],
                  ['Disk', device.disk_percent != null ? Math.round(device.disk_percent) + '%' : '—'],
                  ['Organization', device.organization_name || 'Unassigned'],
                ].map(([k, v]) => (
                  <div key={String(k)} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{k}</p>
                    <p className="mt-1 break-all text-sm font-semibold text-slate-900">{v}</p>
                  </div>
                ))}
              </div>

              <DeviceMetricsChart
                deviceId={String(device.agent_id || device.device_id || device.id)}
                hostname={device.hostname || device.name}
                minutes={60}
                pollMs={15000}
              />
            </>
          )}

          {(tab === 'processes' || tab === 'software') && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-slate-600">
                  Live inventory is requested from the agent. Device must be <strong>online</strong>.
                </p>
                <button
                  type="button"
                  disabled={invBusy || device.status !== 'online'}
                  onClick={() => runInventory(tab === 'processes' ? 'processes' : 'software')}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  {invBusy ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                  Refresh {tab}
                </button>
              </div>
              {invError && (
                <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  {invError}
                </div>
              )}
              <pre className="max-h-[480px] overflow-auto rounded-xl bg-slate-900 p-4 text-[11px] leading-relaxed text-slate-200">
                {(tab === 'processes' ? processOut : softwareOut) ||
                  'Click Refresh to pull a live list from the agent.'}
              </pre>
            </div>
          )}

          {tab === 'remote' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm text-slate-600">
                Open a remote session pre-selected for this agent.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Link
                  href={remoteDeepLink(agentId, 'desktop')}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
                >
                  <ScreenShare size={16} /> Start remote desktop
                </Link>
                <Link
                  href={remoteDeepLink(agentId, 'terminal')}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-3 text-sm font-medium text-slate-800 hover:bg-slate-50"
                >
                  <Terminal size={16} /> Start remote terminal
                </Link>
              </div>
              <p className="mt-3 font-mono text-xs text-slate-400">agent={agentId}</p>
            </div>
          )}
        </div>
      )}
    </ModuleShell>
  );
}
