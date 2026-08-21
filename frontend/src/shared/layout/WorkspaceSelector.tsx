'use client';

import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { useWorkspace } from '@/shared/context/WorkspaceContext';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

type Workspace = { id: string; name: string };

export default function WorkspaceSelector() {
  const { user } = useAuth();
  const { organization, site } = useWorkspace();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selected, setSelected] = useState(user?.tenant_id ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSystemAdmin = useMemo(() => {
    const role = String(user?.role || '').toLowerCase();
    return ['system_admin', 'system-admin', 'superadmin', 'super_admin'].includes(role);
  }, [user?.role]);

  useEffect(() => {
    setSelected(user?.tenant_id ?? '');
  }, [user?.tenant_id]);

  useEffect(() => {
    if (!isSystemAdmin) return;
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/auth/tenant-context/tenants`, {
          credentials: 'include',
          cache: 'no-store',
        });
        if (!response.ok) throw new Error(`Tenant discovery failed (${response.status})`);
        const data = await response.json();
        const rows = Array.isArray(data) ? data : data?.items || data?.tenants || [];
        if (!cancelled) setWorkspaces(rows);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Unable to load tenant context');
      }
    })();
    return () => { cancelled = true; };
  }, [isSystemAdmin]);

  const currentName = workspaces.find((workspace) => workspace.id === selected)?.name || organization?.name || site?.name || 'Select tenant';

  async function selectTenant(tenantId: string) {
    if (!tenantId) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/tenant-context`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data?.detail || 'Unable to set tenant context');
      setSelected(tenantId);
      window.dispatchEvent(new CustomEvent('bhudi:tenant-context-changed', {
        detail: { tenantId, tenantName: data?.tenant_name },
      }));
      window.location.reload();
    } catch (e: any) {
      setError(e?.message || 'Unable to set tenant context');
    } finally {
      setBusy(false);
    }
  }

  if (!isSystemAdmin) return null;

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="bhudi-tenant-context" className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Tenant context
      </label>
      <select
        id="bhudi-tenant-context"
        value={selected}
        disabled={busy || workspaces.length === 0}
        onChange={(event) => void selectTenant(event.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800"
        aria-label="Select tenant context"
      >
        <option value="">{workspaces.length ? 'Select tenant' : 'Loading tenants…'}</option>
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
        ))}
      </select>
      {selected && <span className="text-[11px] text-slate-500">Active: {currentName}</span>}
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
