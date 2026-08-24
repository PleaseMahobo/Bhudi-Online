'use client';

import Link from 'next/link';
import { Building2, CheckCircle2, Monitor, RefreshCw, Server, Ticket, Wifi, XCircle } from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import { useWorkspace } from '@/shared/context/WorkspaceContext';
import { getDevices, listTickets } from '@/lib/api';
import { useCallback, useEffect, useMemo, useState } from 'react';

type Row = Record<string, any>;

export default function SitesPage() {
  const { organizations, sites, organizationId, siteId, setOrganizationId, setSiteId, loading, refresh } = useWorkspace();
  const [devices, setDevices] = useState<Row[]>([]);
  const [tickets, setTickets] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    const [d, t] = await Promise.all([getDevices().catch(() => []), listTickets().catch(() => [])]);
    setDevices(Array.isArray(d) ? d : []);
    setTickets(Array.isArray(t) ? t : []);
    setBusy(false);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const metrics = useMemo(() => organizations.map((org) => {
    const orgSites = sites.filter((site) => site.organization_id === org.id);
    const ids = new Set(orgSites.map((site) => String(site.id)));
    const scoped = devices.filter((d) => ids.has(String(d.site_id ?? d.siteId)) || String(d.organization_id ?? d.organizationId) === String(org.id));
    const online = scoped.filter((d) => ['online', 'active', 'connected'].includes(String(d.status || '').toLowerCase())).length;
    const orgTickets = tickets.filter((t) => String(t.organization_id ?? t.organizationId) === String(org.id) || ids.has(String(t.site_id ?? t.siteId)));
    const openTickets = orgTickets.filter((t) => !['resolved', 'closed', 'done', 'cancelled'].includes(String(t.status || '').toLowerCase())).length;
    return { org, orgSites, devices: scoped.length, online, alerts: 0, tickets: openTickets };
  }), [organizations, sites, devices, tickets]);

  return (
    <ModuleShell>
      <div className="space-y-6 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Sites</h1>
            <p className="mt-1 text-sm text-slate-500">Customer and site operations</p>
          </div>
          <button onClick={() => { void refresh(); void load(); }} disabled={busy || loading} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <RefreshCw size={15} className={busy || loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs text-slate-500">Customers</p><p className="mt-2 text-2xl font-bold">{organizations.length}</p></div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs text-slate-500">Sites</p><p className="mt-2 text-2xl font-bold">{sites.length}</p></div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs text-slate-500">Active context</p><p className="mt-2 text-sm font-semibold">{organizationId ? 'Selected' : 'None'}</p></div>
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          {metrics.map(({ org, orgSites, devices: count, online, tickets: openTickets }) => {
            const active = organizationId === org.id;
            return (
              <section key={org.id} className={`rounded-2xl border bg-white p-5 shadow-sm ${active ? 'border-indigo-300 ring-2 ring-indigo-50' : 'border-slate-200'}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-700"><Building2 size={20} /></span>
                    <div><h2 className="font-semibold text-slate-900">{org.name}</h2><p className="text-xs text-slate-500">{org.org_type || 'Customer'} · {org.status || 'active'}</p></div>
                  </div>
                  {active ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600"><CheckCircle2 size={14}/> Active</span> : null}
                </div>
                <div className="mt-5 grid grid-cols-3 gap-3">
                  <div className="rounded-xl bg-slate-50 p-3"><p className="text-[11px] text-slate-500">Devices</p><p className="mt-1 font-bold">{count}</p></div>
                  <div className="rounded-xl bg-slate-50 p-3"><p className="text-[11px] text-slate-500">Online</p><p className="mt-1 font-bold text-emerald-600">{online}</p></div>
                  <div className="rounded-xl bg-slate-50 p-3"><p className="text-[11px] text-slate-500">Open tickets</p><p className="mt-1 font-bold">{openTickets}</p></div>
                </div>
                <div className="mt-5 space-y-2">
                  {orgSites.length === 0 ? <p className="text-sm text-slate-500">No enabled sites.</p> : orgSites.map((site) => {
                    const selected = siteId === site.id;
                    return <div key={site.id} className="flex items-center justify-between rounded-xl border border-slate-100 px-3 py-2.5">
                      <div><p className="text-sm font-medium text-slate-800">{site.name}</p><p className="text-[11px] text-slate-500">{site.code || 'Site'} · {site.enabled ? 'Enabled' : 'Disabled'}</p></div>
                      <button onClick={() => { setOrganizationId(org.id); setSiteId(site.id); }} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${selected ? 'bg-indigo-600 text-white' : 'border border-slate-200 text-slate-700 hover:bg-slate-50'}`}>{selected ? 'Active' : 'Use site'}</button>
                    </div>;
                  })}
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  <button onClick={() => setOrganizationId(org.id)} className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white"><Wifi size={14}/> Use customer</button>
                  <Link href="/devices" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700"><Monitor size={14}/> Devices</Link>
                  <Link href="/tickets" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700"><Ticket size={14}/> Tickets</Link>
                  <Link href="/agents" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700"><Server size={14}/> Agents</Link>
                </div>
              </section>
            );
          })}
        </div>

        {!loading && organizations.length === 0 && <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">No customer organizations are available for this account.</div>}
      </div>
    </ModuleShell>
  );
}
