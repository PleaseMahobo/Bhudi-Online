'use client';

import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { useWorkspace } from '@/shared/context/WorkspaceContext';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

type Workspace = { id: string; name: string; tenant_id?: string | null };

export default function WorkspaceSelector() {
  const { user } = useAuth();
  const { organization, site } = useWorkspace();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selected, setSelected] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSystemAdmin = useMemo(() => {
    const role = String((user as any)?.role || '').toLowerCase();
    return ['system_admin', 'system-admin', 'superadmin', 'super_admin'].includes(role);
  }, [user]);

  useEffect(() => {
    if (!isSystemAdmin) return;
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/tenants`, { credentials: 'include' });
        if (!response.ok) return;
        const data = await response.json();
        const rows = Array.isArray(data) ? data : data?.items || data?.tenants || [];
        if (!cancelled) setWorkspaces(rows);
      } catch {
        // Keep the existing workspace selector usable if tenant discovery is unavailable.
      }
    })();
    return () => { cancelled = true; };
  }, [isSystemAdmin]);

  const currentName = organization?.name || site?.name || 'Workspace';

  async function selectTenant(tenantId: string) {
    if (!tenantId) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/tenant-context`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
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

  if (!isSystemAdmin || workspaces.length === 0) return null;

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="bhudi-tenant-context" className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Tenant context
      </label>
      <select
        id="bhudi-tenant-context"
        value={selected}
        disabled={busy}
        onChange={(event) => selectTenant(event.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800"
      >
        <option value="">{currentName}</option>
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
        ))}
      </select>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
