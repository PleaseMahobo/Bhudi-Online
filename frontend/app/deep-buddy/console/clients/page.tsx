'use client';

import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Building2, MapPin } from 'lucide-react';

/** Placeholder client/site tree — Tactical-style hierarchy until org APIs are fully wired. */
const SEED = [
  {
    id: 'c1',
    name: 'Acme MSP Lab',
    sites: [
      { id: 's1', name: 'HQ — Main', agents: 3 },
      { id: 's2', name: 'Remote Office', agents: 1 },
    ],
  },
  {
    id: 'c2',
    name: 'Northwind Traders',
    sites: [{ id: 's3', name: 'Warehouse', agents: 2 }],
  },
];

export default function DeepBuddyClientsPage() {
  const [open, setOpen] = useState<Record<string, boolean>>({ c1: true });
  const tree = useMemo(() => SEED, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Clients & sites</h1>
        <p className="text-sm text-slate-500">
          Tactical RMM-style hierarchy. Assign agents from the Agents list or device detail.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        {tree.map((client) => {
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
                  {client.sites.length} site{client.sites.length === 1 ? '' : 's'}
                </span>
              </button>
              {isOpen && (
                <ul className="pb-2 pl-12">
                  {client.sites.map((site) => (
                    <li
                      key={site.id}
                      className="flex items-center gap-2 py-1.5 text-sm text-slate-700"
                    >
                      <MapPin size={14} className="text-slate-400" />
                      {site.name}
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                        {site.agents} agents
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-slate-500">
        Seed data for UI structure. Live assignment uses device assignment APIs on the Bhudi backend.
      </p>
    </div>
  );
}
