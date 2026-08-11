'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Monitor, Wifi, WifiOff, AlertTriangle } from 'lucide-react';

const API = (
  process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

type Agent = {
  agent_id?: string;
  id?: string;
  hostname?: string;
  status?: string;
  platform?: string;
  last_seen?: string;
};

export default function DeepBuddyDashboard() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(API + '/api/v1/runtime/agents');
        const data = await res.json().catch(() => ({}));
        if (!cancelled) setAgents(data.agents || []);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load agents');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const online = agents.filter((a) => (a.status || '').toLowerCase() === 'online').length;
  const offline = agents.length - online;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">
          Tactical-style overview of your Deep Buddy agent fleet
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={Monitor} label="Agents" value={String(agents.length)} tone="slate" />
        <StatCard icon={Wifi} label="Online" value={String(online)} tone="emerald" />
        <StatCard icon={WifiOff} label="Offline / other" value={String(offline)} tone="amber" />
      </div>

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <AlertTriangle className="mb-1 inline" size={14} /> {error}
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Recent agents</h2>
          <Link
            href="/deep-buddy/console/agents"
            className="text-xs font-medium text-cyan-700 hover:underline"
          >
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Hostname</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Platform</th>
                <th className="px-4 py-2">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {agents.slice(0, 8).map((a) => (
                <tr key={a.agent_id || a.id} className="border-t border-slate-100">
                  <td className="px-4 py-2.5 font-medium text-slate-800">
                    {a.hostname || a.agent_id || '—'}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusPill status={a.status} />
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{a.platform || '—'}</td>
                  <td className="px-4 py-2.5 text-slate-500">{a.last_seen || '—'}</td>
                </tr>
              ))}
              {agents.length === 0 && !error && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                    No agents yet. Install the Bhudi native agent and enroll against this backend.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  value: string;
  tone: 'slate' | 'emerald' | 'amber';
}) {
  const tones = {
    slate: 'border-slate-200 bg-white',
    emerald: 'border-emerald-200 bg-emerald-50',
    amber: 'border-amber-200 bg-amber-50',
  };
  return (
    <div className={`rounded-2xl border p-4 shadow-sm ${tones[tone]}`}>
      <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
        <Icon size={14} />
        {label}
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

function StatusPill({ status }: { status?: string }) {
  const s = (status || 'unknown').toLowerCase();
  const cls =
    s === 'online'
      ? 'bg-emerald-100 text-emerald-800'
      : s === 'offline'
        ? 'bg-slate-200 text-slate-700'
        : 'bg-amber-100 text-amber-900';
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {status || 'unknown'}
    </span>
  );
}
