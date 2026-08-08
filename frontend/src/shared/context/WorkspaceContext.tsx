'use client';

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

export type WorkspaceOrganization = { id: string; tenant_id: string; name: string; org_type: string; status: string; parent_id?: string | null };
export type WorkspaceSite = { id: string; tenant_id: string; organization_id: string; name: string; code?: string | null; enabled: boolean };
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';
function token() { if (typeof window === 'undefined') return null; return localStorage.getItem('access_token'); }
async function getJson<T>(path: string): Promise<T> { const response = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token() || ''}` } }); if (!response.ok) throw new Error(`Workspace request failed: ${response.status}`); return response.json(); }

type WorkspaceContextValue = { organizations: WorkspaceOrganization[]; sites: WorkspaceSite[]; organization: WorkspaceOrganization | null; site: WorkspaceSite | null; organizationId: string | null; siteId: string | null; setOrganizationId: (id: string | null) => void; setSiteId: (id: string | null) => void; loading: boolean; refresh: () => Promise<void> };
const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [organizations, setOrganizations] = useState<WorkspaceOrganization[]>([]);
  const [sites, setSites] = useState<WorkspaceSite[]>([]);
  const [organizationId, setOrganizationIdState] = useState<string | null>(null);
  const [siteId, setSiteIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const rows = await getJson<WorkspaceOrganization[]>('/api/v1/msp/organizations?status=active');
      setOrganizations(Array.isArray(rows) ? rows : []);
      if (typeof window !== 'undefined') { const savedOrg = localStorage.getItem('bhudi.workspace.organization'); setOrganizationIdState(rows.find((row) => row.id === savedOrg)?.id ?? null); }
    } catch { setOrganizations([]); } finally { setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!organizationId) { setSites([]); setSiteIdState(null); return; }
    void getJson<WorkspaceSite[]>(`/api/v1/msp/sites?organization_id=${encodeURIComponent(organizationId)}&enabled_only=true`).then((rows) => { setSites(Array.isArray(rows) ? rows : []); const saved = typeof window !== 'undefined' ? localStorage.getItem('bhudi.workspace.site') : null; setSiteIdState(rows.some((row) => row.id === saved) ? saved : null); }).catch(() => { setSites([]); setSiteIdState(null); });
  }, [organizationId]);
  const setOrganizationId = (id: string | null) => { setOrganizationIdState(id); setSiteIdState(null); if (typeof window !== 'undefined') { if (id) localStorage.setItem('bhudi.workspace.organization', id); else localStorage.removeItem('bhudi.workspace.organization'); localStorage.removeItem('bhudi.workspace.site'); } };
  const setSiteId = (id: string | null) => { setSiteIdState(id); if (typeof window !== 'undefined') { if (id) localStorage.setItem('bhudi.workspace.site', id); else localStorage.removeItem('bhudi.workspace.site'); } };
  const value = useMemo(() => ({ organizations, sites, organization: organizations.find((row) => row.id === organizationId) || null, site: sites.find((row) => row.id === siteId) || null, organizationId, siteId, setOrganizationId, setSiteId, loading, refresh }), [organizations, sites, organizationId, siteId, loading]);
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}
export function useWorkspace() { const value = useContext(WorkspaceContext); if (!value) throw new Error('useWorkspace must be used inside WorkspaceProvider'); return value; }
