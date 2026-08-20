'use client';

import { useState } from 'react';
import { Building2, ChevronDown, Globe2, MapPin, RefreshCw } from 'lucide-react';
import { useWorkspace } from '@/shared/context/WorkspaceContext';

export default function WorkspaceSelector() {
  const { organizations, sites, organization, site, organizationId, siteId, setOrganizationId, setSiteId, loading, refresh } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const label = organization ? `${organization.name}${site ? ` · ${site.name}` : ''}` : 'All customers';

  async function selectOrganization(id: string | null) {
    setSwitching(true);
    try {
      await setOrganizationId(id);
      setOpen(false);
    } catch (error) {
      console.error('Failed to switch workspace:', error);
    } finally {
      setSwitching(false);
    }
  }

  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)} disabled={switching} className="flex max-w-[280px] items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-left shadow-sm hover:bg-slate-50 disabled:opacity-60" aria-expanded={open}>
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-indigo-50 text-indigo-600"><Building2 size={15} /></span>
        <span className="min-w-0 hidden sm:block"><span className="block truncate text-xs font-semibold text-slate-800">{label}</span><span className="block truncate text-[10px] text-slate-500">{organization ? 'Customer workspace' : 'MSP workspace'}</span></span>
        <ChevronDown size={14} className="ml-auto shrink-0 text-slate-400" />
      </button>
      {open && <div className="absolute left-0 top-11 z-50 w-[310px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3"><div><p className="text-sm font-semibold text-slate-900">Workspace</p><p className="text-xs text-slate-500">Choose the operational context</p></div><button type="button" onClick={() => void refresh()} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" aria-label="Refresh customers"><RefreshCw size={14} className={loading ? 'animate-spin' : ''} /></button></div>
        <div className="max-h-[360px] overflow-y-auto p-2">
          <button type="button" disabled={switching} onClick={() => void selectOrganization(null)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left ${!organizationId ? 'bg-indigo-50' : 'hover:bg-slate-50'}`}><Globe2 size={16} className="text-indigo-500" /><span><span className="block text-sm font-medium text-slate-900">All customers</span><span className="block text-xs text-slate-500">MSP-wide operational view</span></span></button>
          {organizations.map((org) => <div key={org.id} className="mt-1"><button type="button" disabled={switching} onClick={() => void selectOrganization(org.id)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left ${organizationId === org.id ? 'bg-indigo-50' : 'hover:bg-slate-50'}`}><Building2 size={16} className="text-slate-500" /><span className="min-w-0"><span className="block truncate text-sm font-medium text-slate-900">{org.name}</span><span className="block text-xs capitalize text-slate-500">{org.org_type} · {org.status}</span></span></button>{organizationId === org.id && <div className="ml-5 border-l border-slate-200 pl-2">{sites.length ? sites.map((item) => <button key={item.id} type="button" onClick={() => { setSiteId(item.id); setOpen(false); }} className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs ${siteId === item.id ? 'bg-indigo-50 font-semibold text-indigo-700' : 'text-slate-600 hover:bg-slate-50'}`}><MapPin size={13} />{item.name}</button>) : <p className="px-3 py-2 text-[11px] text-slate-400">No active sites</p>}</div>}</div>)}
          {!organizations.length && !loading && <p className="px-3 py-6 text-center text-xs text-slate-500">No customer organizations available.</p>}
        </div>
      </div>}
    </div>
  );
}
