'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Building2, KeyRound, RefreshCw, ShieldCheck, Users, UserCheck, UserX } from 'lucide-react';
import ModuleShell, { Btn, Err, Panel } from '@/shared/components/ModuleShell';
import { useAuth } from '@/shared/auth/AuthContext';
import {
  getAdminOverview,
  getAdminPermissions,
  getAdminRoles,
  getAdminTenants,
  getAdminUsers,
  updateAdminUser,
} from '@/lib/api-modules';

const inputCls = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/30';

type Tab = 'overview' | 'users' | 'tenants' | 'rbac';

export default function AdministratorPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>('overview');
  const [overview, setOverview] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [tenants, setTenants] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [permissions, setPermissions] = useState<any[]>([]);
  const [filter, setFilter] = useState('');
  const [tenantFilter, setTenantFilter] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPlatformAdmin = String(user?.role || '').toLowerCase() === 'enterprise_admin';

  const load = useCallback(async () => {
    if (!isPlatformAdmin) return;
    setBusy(true);
    setError(null);
    try {
      const [o, u, t, r, p] = await Promise.all([
        getAdminOverview(),
        getAdminUsers(),
        getAdminTenants(),
        getAdminRoles(),
        getAdminPermissions(),
      ]);
      setOverview(o);
      setUsers(o?.users ? u.users || [] : u.users || []);
      setTenants(t.tenants || []);
      setRoles(r.roles || []);
      setPermissions(p.permissions || []);
    } catch (e: any) {
      setError(e?.message || 'Administrator data could not be loaded');
    } finally {
      setBusy(false);
    }
  }, [isPlatformAdmin]);

  useEffect(() => {
    if (!loading && !user) router.replace('/login');
  }, [loading, user, router]);

  useEffect(() => { void load(); }, [load]);

  const filteredUsers = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return users.filter((u) => {
      if (tenantFilter && String(u.tenant_id) !== tenantFilter) return false;
      if (!q) return true;
      return [u.email, u.first_name, u.last_name, u.role, u.tenant_name, ...(u.roles || [])]
        .filter(Boolean).join(' ').toLowerCase().includes(q);
    });
  }, [users, filter, tenantFilter]);

  async function updateUser(id: string, data: any) {
    setBusy(true);
    setError(null);
    try {
      await updateAdminUser(id, data);
      await load();
    } catch (e: any) {
      setError(e?.message || 'User update failed');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <ModuleShell title="Administrator"><div className="text-slate-500">Verifying administrator access…</div></ModuleShell>;
  if (!user) return null;

  if (!isPlatformAdmin) {
    return (
      <ModuleShell title="Administrator" subtitle="Platform administration">
        <Panel title="Access denied">
          <p className="text-sm text-slate-600">This workspace is restricted to the enterprise administrator role.</p>
        </Panel>
      </ModuleShell>
    );
  }

  const statCards = [
    ['Users', overview?.users ?? '—', Users],
    ['Active users', overview?.active_users ?? '—', UserCheck],
    ['Tenants', overview?.tenants ?? '—', Building2],
    ['RBAC roles', overview?.roles ?? '—', ShieldCheck],
    ['Permissions', overview?.permissions ?? '—', KeyRound],
  ] as const;

  return (
    <ModuleShell
      title="Administrator"
      subtitle="Platform-wide users, tenant memberships, roles, permissions and access control"
      breadcrumbs={[{ label: 'Administrator' }]}
    >
      <Err error={error} />
      <div className="mb-5 flex flex-wrap items-center gap-2">
        {(['overview', 'users', 'tenants', 'rbac'] as Tab[]).map((id) => (
          <button key={id} onClick={() => setTab(id)} className={`rounded-xl px-4 py-2 text-sm font-medium ${tab === id ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}>
            {id === 'rbac' ? 'RBAC & permissions' : id[0].toUpperCase() + id.slice(1)}
          </button>
        ))}
        <Btn variant="ghost" onClick={() => void load()}><RefreshCw size={15} className="mr-1 inline" /> Refresh</Btn>
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            {statCards.map(([label, value, Icon]) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <Icon size={18} className="mb-3 text-indigo-600" />
                <div className="text-2xl font-semibold text-slate-900">{value}</div>
                <div className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
              </div>
            ))}
          </div>
          <Panel title="Administrator scope">
            <div className="grid gap-4 md:grid-cols-3">
              <div><p className="text-xs uppercase tracking-wide text-slate-400">Identity</p><p className="mt-1 font-medium">{user.email}</p></div>
              <div><p className="text-xs uppercase tracking-wide text-slate-400">Role</p><p className="mt-1 font-medium">enterprise_admin</p></div>
              <div><p className="text-xs uppercase tracking-wide text-slate-400">Control plane</p><p className="mt-1 font-medium">All tenants · users · RBAC</p></div>
            </div>
          </Panel>
        </div>
      )}

      {tab === 'users' && (
        <Panel title={`Users (${filteredUsers.length})`}>
          <div className="mb-4 grid gap-2 md:grid-cols-2">
            <input className={inputCls} placeholder="Search email, name, role or tenant…" value={filter} onChange={(e) => setFilter(e.target.value)} />
            <select className={inputCls} value={tenantFilter} onChange={(e) => setTenantFilter(e.target.value)}>
              <option value="">All tenant memberships</option>
              {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-3">User</th><th className="px-3 py-3">Tenant</th><th className="px-3 py-3">RBAC</th><th className="px-3 py-3">MFA</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Actions</th>
              </tr></thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <tr key={u.id} className="border-b border-slate-100">
                    <td className="px-3 py-3"><div className="font-medium text-slate-900">{u.first_name || u.last_name ? [u.first_name, u.last_name].filter(Boolean).join(' ') : u.email}</div><div className="text-xs text-slate-500">{u.email}</div></td>
                    <td className="px-3 py-3"><div className="font-medium">{u.tenant_name || 'No tenant'}</div><div className="text-[10px] text-slate-400">{u.tenant_id || '—'}</div></td>
                    <td className="px-3 py-3">
                      <select className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs" value={u.role} onChange={(e) => void updateUser(u.id, { role: e.target.value })}>
                        {roles.map((r) => <option key={r.id} value={r.name}>{r.name}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-3">{u.mfa_enabled ? <span className="text-emerald-700">Enabled</span> : <span className="text-slate-400">Off</span>}</td>
                    <td className="px-3 py-3">{u.active ? <span className="text-emerald-700">Active</span> : <span className="text-red-600">Disabled</span>}</td>
                    <td className="px-3 py-3">
                      <button className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs hover:bg-slate-50" disabled={busy || u.id === user.id} onClick={() => void updateUser(u.id, { active: !u.active })}>
                        {u.active ? <><UserX size={13} className="mr-1 inline" />Disable</> : <><UserCheck size={13} className="mr-1 inline" />Enable</>}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredUsers.length === 0 && <div className="py-10 text-center text-sm text-slate-500">No users match the filter.</div>}
          </div>
        </Panel>
      )}

      {tab === 'tenants' && (
        <Panel title={`Tenant memberships (${tenants.length})`}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {tenants.map((t) => (
              <div key={t.id} className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-start justify-between gap-3"><Building2 size={18} className="text-indigo-600" /><span className="text-xs text-slate-400">{t.id.slice(0, 8)}…</span></div>
                <h3 className="mt-3 font-semibold text-slate-900">{t.name}</h3>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs"><div className="rounded-lg bg-slate-50 p-2"><b>{t.user_count}</b><br />users</div><div className="rounded-lg bg-slate-50 p-2"><b>{t.agent_count}</b><br />agents</div><div className="rounded-lg bg-slate-50 p-2"><b>{t.device_count}</b><br />devices</div></div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {tab === 'rbac' && (
        <div className="grid gap-6 xl:grid-cols-2">
          <Panel title={`Roles (${roles.length})`}>
            <div className="space-y-3">{roles.map((r) => <div key={r.id} className="rounded-xl border border-slate-200 p-4"><div className="flex justify-between"><span className="font-semibold">{r.name}</span>{r.system && <span className="text-xs text-purple-700">system</span>}</div><p className="mt-1 text-xs text-slate-500">{r.description || 'No description'}</p><div className="mt-3 flex flex-wrap gap-1">{(r.permissions || []).map((p: string) => <span key={p} className="rounded-full bg-slate-100 px-2 py-1 text-[10px] text-slate-600">{p}</span>)}</div></div>)}</div>
          </Panel>
          <Panel title={`Permissions (${permissions.length})`}>
            <div className="max-h-[620px] overflow-auto divide-y divide-slate-100">{permissions.map((p) => <div key={p.id} className="py-3"><div className="font-medium text-sm">{p.name}</div><div className="text-xs text-slate-500">{p.resource} · {p.action}{p.description ? ` · ${p.description}` : ''}</div></div>)}</div>
          </Panel>
        </div>
      )}
    </ModuleShell>
  );
}
