'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

const API = (
  process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

type Agent = {
  agent_id: string;
  hostname?: string;
  status?: string;
  platform?: string;
  last_seen?: string;
  ip_address?: string;
  agent_version?: string;
};

export default function DeepBuddyAgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [q, setQ] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(API + '/api/v1/runtime/agents');
        const data = await res.json().catch(() => ({}));
        if (!cancelled) setAgents(data.agents || []);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = agents.filter((a) => {
    const hay = `${a.hostname || ''} ${a.agent_id} ${a.platform || ''}`.toLowerCase();
    return hay.includes(q.toLowerCase());
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Agents</h1>
          <p className="text-sm text-slate-500">
            Tactical-style agent list · data from Bhudi runtime enroll
          </p>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search hostname, id, platform…"
          className="w-full max-w-xs rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
        />
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Hostname</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Platform</th>
              <th className="px-4 py-2">Version</th>
              <th className="px-4 py-2">IP</th>
              <th className="px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a) => (
              <tr key={a.agent_id} className="border-t border-slate-100 hover:bg-slate-50/80">
                <td className="px-4 py-2.5 font-medium text-slate-900">
                  {a.hostname || a.agent_id}
                </td>
                <td className="px-4 py-2.5 capitalize text-slate-700">{a.status || '—'}</td>
                <td className="px-4 py-2.5 text-slate-600">{a.platform || '—'}</td>
                <td className="px-4 py-2.5 text-slate-600">{a.agent_version || '—'}</td>
                <td className="px-4 py-2.5 text-slate-600">{a.ip_address || '—'}</td>
                <td className="px-4 py-2.5">
                  <div className="flex gap-2">
                    <Link
                      href={`/devices/${a.agent_id}`}
                      className="text-xs font-medium text-cyan-700 hover:underline"
                    >
                      Detail
                    </Link>
                    <Link
                      href={`/remote?agent=${a.agent_id}`}
                      className="text-xs font-medium text-slate-600 hover:underline"
                    >
                      Remote
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                  No matching agents.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
