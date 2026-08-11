'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronRight, Building2, MapPin, RefreshCw, Monitor } from 'lucide-react';

const API = (
  process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

type AgentRef = {
  agent_id?: string;
  hostname?: string;
  status?: string;
  platform?: string;
};

type SiteNode = {
  id: string;
  name: string;
  agent_count: number;
  agents?: AgentRef[];
};

type ClientNode = {
  id: string;
  name: string;
  org_type?: string;
  source?: string;
  sites: SiteNode[];
};

export default function DeepBuddyClientsPage() {
  const [clients, setClients] = useState<ClientNode[]>([]);
  const [source, setSource] = useState('');
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(API + '/api/v1/deep-buddy/tree');
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      const list: ClientNode[] = data.clients || [];
      setClients(list);
      setSource(data.source || '');
      setCounts(data.counts || {});
      setOpen((prev) => {
        const next = { ...prev };
        list.forEach((c, i) => {
          if (next[c.id] === undefined) next[c.id] = i === 0;
        });
        return next;
      });
    } catch (e: any) {
      setError(e?.message || 'Failed to load tree');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Clients & sites</h1>
          <p className="text-sm text-slate-500">
            Live Tactical-style hierarchy
            {source ? (
              <>
                {' '}
                · source: <span className="font-medium text-slate-700">{source}</span>
              </>
            ) : null}
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {(counts.clients != null || counts.runtime_agents != null) && (
        <div className="flex flex-wrap gap-3 text-xs text-slate-600">
          <span className="rounded-full bg-slate-100 px-2.5 py-1">{counts.clients ?? 0} clients</span>
          <span className="rounded-full bg-slate-100 px-2.5 py-1">{counts.sites ?? 0} sites</span>
          <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-cyan-800">
            {counts.runtime_agents ?? 0} runtime agents
          </span>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading && clients.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-500">Loading tree…</p>
        )}
        {clients.map((client) => {
          const isOpen = open[client.id];
          return (
            <div key={client.id} className="border-b border-slate-100 last:border-0">
              <button
                type="button"
                onClick={() => setOpen((o) => ({ ...o, [client.id]: !o[client.id] }))}
                className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-slate-50"
              >
                {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                <Building2 size={16} className="text-cyan-700" />
                <span className="font-medium text-slate-900">{client.name}</span>
                <span className="text-xs text-slate-400">
                  {client.sites?.length || 0} site{(client.sites?.length || 0) === 1 ? '' : 's'}
                </span>
              </button>
              {isOpen && (
                <ul className="pb-3 pl-12">
                  {(client.sites || []).map((site) => (
                    <li key={site.id} className="py-1.5">
                      <div className="flex items-center gap-2 text-sm text-slate-700">
                        <MapPin size={14} className="text-slate-400" />
                        {site.name}
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                          {site.agent_count} agents
                        </span>
                      </div>
                      {(site.agents || []).length > 0 && (
                        <ul className="mt-1 space-y-0.5 pl-6">
                          {site.agents!.map((a) => (
                            <li
                              key={a.agent_id}
                              className="flex items-center gap-2 text-xs text-slate-600"
                            >
                              <Monitor size={12} className="text-slate-400" />
                              <Link
                                href={`/devices/${a.agent_id}`}
                                className="font-medium text-cyan-700 hover:underline"
                              >
                                {a.hostname || a.agent_id}
                              </Link>
                              <span className="capitalize text-slate-400">{a.status}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
        {!loading && clients.length === 0 && !error && (
          <p className="px-4 py-8 text-center text-sm text-slate-500">No clients yet.</p>
        )}
      </div>

      <p className="text-xs text-slate-500">
        Data from <code className="rounded bg-slate-100 px-1">GET /api/v1/deep-buddy/tree</code>
      </p>
    </div>
  );
}
