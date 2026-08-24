'use client';

import { useMemo, useState } from 'react';
import { AlertTriangle, Bell, CheckCircle2, Info, RefreshCw, Search, ShieldAlert } from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import { useWorkspace } from '@/shared/context/WorkspaceContext';

type AlertRow = { id: string; severity: 'critical' | 'warning' | 'info' | 'recovery'; title: string; device?: string; site?: string; status: 'active' | 'acknowledged' | 'resolved'; timestamp: string };

const demo: AlertRow[] = [];

export default function AlertsPage() {
  const { organization, site } = useWorkspace();
  const [alerts, setAlerts] = useState<AlertRow[]>(demo);
  const [severity, setSeverity] = useState<'all' | AlertRow['severity']>('all');
  const [status, setStatus] = useState<'all' | AlertRow['status']>('all');
  const [query, setQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const filtered = useMemo(() => alerts.filter((a) => {
    if (severity !== 'all' && a.severity !== severity) return false;
    if (status !== 'all' && a.status !== status) return false;
    if (organization && a.site && a.site !== organization.name && a.site !== site?.name) return false;
    if (query && !`${a.title} ${a.device || ''} ${a.site || ''}`.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  }), [alerts, severity, status, organization, site, query]);

  const counts = { critical: filtered.filter(a => a.severity === 'critical').length, warning: filtered.filter(a => a.severity === 'warning').length, info: filtered.filter(a => a.severity === 'info').length, active: filtered.filter(a => a.status === 'active').length };

  return <ModuleShell title="Alerts" subtitle="Operational alerts across the active customer and site context." breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Alerts' }]} actions={<button onClick={() => { setRefreshing(true); setTimeout(() => setRefreshing(false), 400); }} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"><RefreshCw size={15} className={refreshing ? 'animate-spin' : ''}/>Refresh</button>}>
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-red-200 bg-white p-5"><p className="text-xs text-slate-500">Critical</p><p className="mt-2 text-2xl font-bold text-red-700">{counts.critical}</p></div>
        <div className="rounded-2xl border border-amber-200 bg-white p-5"><p className="text-xs text-slate-500">Warnings</p><p className="mt-2 text-2xl font-bold text-amber-700">{counts.warning}</p></div>
        <div className="rounded-2xl border border-blue-200 bg-white p-5"><p className="text-xs text-slate-500">Information</p><p className="mt-2 text-2xl font-bold text-blue-700">{counts.info}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-xs text-slate-500">Active</p><p className="mt-2 text-2xl font-bold text-slate-900">{counts.active}</p></div>
      </div>
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        {(['all','critical','warning','info'] as const).map(v => <button key={v} onClick={() => setSeverity(v)} className={`rounded-full border px-3 py-1.5 text-xs font-semibold capitalize ${severity === v ? 'border-indigo-200 bg-indigo-50 text-indigo-800' : 'border-slate-200 text-slate-600'}`}>{v}</button>)}
        <select value={status} onChange={e => setStatus(e.target.value as any)} className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium"><option value="all">All statuses</option><option value="active">Active</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></select>
        <div className="relative ml-auto min-w-[220px] max-w-sm flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search alerts, devices, sites…" className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm"/></div>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {filtered.length === 0 ? <div className="p-12 text-center"><CheckCircle2 size={28} className="mx-auto text-emerald-500"/><p className="mt-3 text-sm font-semibold text-slate-800">No alerts in this context</p><p className="mt-1 text-xs text-slate-500">New alert events will appear here when the alert stream is connected.</p></div> : filtered.map(a => <div key={a.id} className="flex flex-wrap items-center gap-4 border-b border-slate-100 px-5 py-4 last:border-0"><span className="rounded-xl bg-slate-50 p-2">{a.severity === 'critical' ? <ShieldAlert size={18}/> : a.severity === 'warning' ? <AlertTriangle size={18}/> : a.severity === 'info' ? <Info size={18}/> : <Bell size={18}/>}</span><div className="min-w-[220px] flex-1"><p className="text-sm font-semibold text-slate-900">{a.title}</p><p className="text-xs text-slate-500">{a.device || 'System'} · {a.site || site?.name || organization?.name || 'Current context'}</p></div><span className="text-xs text-slate-500">{a.timestamp}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold capitalize">{a.status}</span></div>)}
      </div>
    </div>
  </ModuleShell>;
}
