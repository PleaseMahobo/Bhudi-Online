'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Bell, CheckCircle2, Info, RefreshCw, Search, ShieldAlert } from 'lucide-react';
import ModuleShell from '@/shared/components/ModuleShell';
import { useWorkspace } from '@/shared/context/WorkspaceContext';

type AlertRow = { id: string; severity: 'critical' | 'warning' | 'info' | 'recovery' | string; title: string; device?: string; site?: string; status: 'active' | 'acknowledged' | 'resolved' | string; timestamp: string };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers); headers.set('Accept', 'application/json');
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, { ...init, headers, credentials: 'include', cache: 'no-store' });
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body?.detail || response.statusText); }
  return response.status === 204 ? undefined as T : response.json();
}

function normalize(a: any): AlertRow { return { id: String(a.id), severity: String(a.severity || 'info').toLowerCase(), title: a.message || a.type || 'Alert', device: a.device_name || a.device_id || undefined, site: a.site_name || undefined, status: a.status || (a.resolved ? 'resolved' : 'active'), timestamp: a.created_at || new Date().toISOString() }; }

export default function AlertsPage() {
  const { organization, site } = useWorkspace();
  const [alerts, setAlerts] = useState<AlertRow[]>([]); const [severity, setSeverity] = useState<'all' | string>('all'); const [status, setStatus] = useState<'all' | string>('all'); const [query, setQuery] = useState(''); const [refreshing, setRefreshing] = useState(false); const [error, setError] = useState('');

  const load = useCallback(async () => { setRefreshing(true); setError(''); try { const rows = await api<any[]>('/api/v1/alerts'); setAlerts((rows || []).map(normalize)); } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load alerts'); } finally { setRefreshing(false); } }, []);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/alerts`);
    ws.onmessage = (event) => { try { const message = JSON.parse(event.data); if (message.type === 'alert.updated') { const id = String(message.data.id); setAlerts((current) => current.map((a) => a.id === id ? { ...a, status: message.data.status } : a)); } } catch {} };
    return () => ws.close();
  }, []);

  const mutate = async (id: string, action: 'acknowledge' | 'resolve') => { try { const updated = await api<any>(`/api/v1/alerts/${encodeURIComponent(id)}/${action}`, { method: 'POST' }); setAlerts((current) => current.map((a) => a.id === id ? normalize(updated) : a)); } catch (e) { setError(e instanceof Error ? e.message : `Unable to ${action} alert`); } };

  const filtered = useMemo(() => alerts.filter((a) => {
    if (severity !== 'all' && a.severity !== severity) return false;
    if (status !== 'all' && a.status !== status) return false;
    if (organization && a.site && a.site !== organization.name && a.site !== site?.name) return false;
    return !query || `${a.title} ${a.device || ''} ${a.site || ''}`.toLowerCase().includes(query.toLowerCase());
  }), [alerts, severity, status, organization, site, query]);

  const counts = { critical: filtered.filter(a => a.severity === 'critical').length, warning: filtered.filter(a => a.severity === 'warning').length, info: filtered.filter(a => a.severity === 'info').length, active: filtered.filter(a => a.status === 'active').length };

  return <ModuleShell title="Alerts" subtitle="Live, tenant-scoped operational alerts." breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Alerts' }]} actions={<button onClick={() => void load()} disabled={refreshing} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"><RefreshCw size={15} className={refreshing ? 'animate-spin' : ''}/>Refresh</button>}>
    <div className="space-y-5">
      {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="grid gap-4 sm:grid-cols-4"><div className="rounded-2xl border border-red-200 bg-white p-5"><p className="text-xs text-slate-500">Critical</p><p className="mt-2 text-2xl font-bold text-red-700">{counts.critical}</p></div><div className="rounded-2xl border border-amber-200 bg-white p-5"><p className="text-xs text-slate-500">Warnings</p><p className="mt-2 text-2xl font-bold text-amber-700">{counts.warning}</p></div><div className="rounded-2xl border border-blue-200 bg-white p-5"><p className="text-xs text-slate-500">Information</p><p className="mt-2 text-2xl font-bold text-blue-700">{counts.info}</p></div><div className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-xs text-slate-500">Active</p><p className="mt-2 text-2xl font-bold text-slate-900">{counts.active}</p></div></div>
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">{['all','critical','warning','info'].map(v => <button key={v} onClick={() => setSeverity(v)} className={`rounded-full border px-3 py-1.5 text-xs font-semibold capitalize ${severity === v ? 'border-indigo-200 bg-indigo-50 text-indigo-800' : 'border-slate-200 text-slate-600'}`}>{v}</button>)}<select value={status} onChange={e => setStatus(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium"><option value="all">All statuses</option><option value="active">Active</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></select><div className="relative ml-auto min-w-[220px] max-w-sm flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search alerts, devices, sites…" className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm"/></div></div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">{filtered.length === 0 ? <div className="p-12 text-center"><CheckCircle2 size={28} className="mx-auto text-emerald-500"/><p className="mt-3 text-sm font-semibold text-slate-800">No alerts in this context</p><p className="mt-1 text-xs text-slate-500">The live alert stream is connected.</p></div> : filtered.map(a => <div key={a.id} className="flex flex-wrap items-center gap-4 border-b border-slate-100 px-5 py-4 last:border-0"><span className="rounded-xl bg-slate-50 p-2">{a.severity === 'critical' ? <ShieldAlert size={18}/> : a.severity === 'warning' ? <AlertTriangle size={18}/> : a.severity === 'info' ? <Info size={18}/> : <Bell size={18}/>}</span><div className="min-w-[220px] flex-1"><p className="text-sm font-semibold text-slate-900">{a.title}</p><p className="text-xs text-slate-500">{a.device || 'System'} · {a.site || site?.name || organization?.name || 'Current context'}</p></div><span className="text-xs text-slate-500">{a.timestamp}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold capitalize">{a.status}</span>{a.status === 'active' && <button onClick={() => void mutate(a.id, 'acknowledge')} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700">Acknowledge</button>}{a.status !== 'resolved' && <button onClick={() => void mutate(a.id, 'resolve')} className="rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-white">Resolve</button>}</div>)}</div>
    </div>
  </ModuleShell>;
}
