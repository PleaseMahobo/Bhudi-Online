'use client';

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { listOrganizations, listSites } from '@/lib/api';
import { setTenantContext } from '@/lib/tenant-context';

export type WorkspaceOrganization = { id: string; tenant_id: string; name: string; org_type: string; status: string; parent_id?: string | null };
export type WorkspaceSite = { id: string; tenant_id: string; organization_id: string; name: string; code?: string | null; enabled: boolean };

type WorkspaceContextValue = {
  organizations: WorkspaceOrganization[];
  sites: WorkspaceSite[];
  organization: WorkspaceOrganization | null;
  site: WorkspaceSite | null;
  organizationId: string | null;
  siteId: string | null;
  setOrganizationId: (id: string | null) => Promise<void>;
  setSiteId: (id: string | null) => void;
  loading: boolean;
  refresh: () => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [organizations, setOrganizations] = useState<WorkspaceOrganization[]>([]);
  const [sites, setSites] = useState<WorkspaceSite[]>([]);
  const [organizationId, setOrganizationIdState] = useState<string | null>(null);
  const [siteId, setSiteIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const applyTenantContext = async (orgId: string | null, rows: WorkspaceOrganization[]) => {
    if (!orgId) {
      await setTenantContext(null);
      return;
    }
    const organization = rows.find((row) => row.id === orgId);
    if (!organization?.tenant_id) throw new Error('Selected customer has no tenant association');
    await setTenantContext(organization.tenant_id);
  };

  const refresh = async () => {
    setLoading(true);
    try {
      const rows = await listOrganizations({ status: 'active' });
      const organizations = Array.isArray(rows) ? rows as WorkspaceOrganization[] : [];
      setOrganizations(organizations);
      if (typeof window !== 'undefined') {
        const savedOrg = localStorage.getItem('bhudi.workspace.organization');
        const nextOrg = organizations.find((row) => row.id === savedOrg)?.id ?? null;
        setOrganizationIdState(nextOrg);
        if (nextOrg) await applyTenantContext(nextOrg, organizations);
      }
    } catch {
      setOrganizations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  useEffect(() => {
    if (!organizationId) {
      setSites([]);
      setSiteIdState(null);
      return;
    }
    void listSites({ organization_id: organizationId, enabled_only: true })
      .then((rows) => {
        setSites(Array.isArray(rows) ? rows as WorkspaceSite[] : []);
        const saved = typeof window !== 'undefined' ? localStorage.getItem('bhudi.workspace.site') : null;
        setSiteIdState(rows.some((row: any) => row.id === saved) ? saved : null);
      })
      .catch(() => { setSites([]); setSiteIdState(null); });
  }, [organizationId]);

  const setOrganizationId = async (id: string | null) => {
    await applyTenantContext(id, organizations);
    setOrganizationIdState(id);
    setSiteIdState(null);
    if (typeof window !== 'undefined') {
      if (id) localStorage.setItem('bhudi.workspace.organization', id); else localStorage.removeItem('bhudi.workspace.organization');
      localStorage.removeItem('bhudi.workspace.site');
    }
  };

  const setSiteId = (id: string | null) => {
    setSiteIdState(id);
    if (typeof window !== 'undefined') {
      if (id) localStorage.setItem('bhudi.workspace.site', id); else localStorage.removeItem('bhudi.workspace.site');
    }
  };

  const value = useMemo(() => ({ organizations, sites, organization: organizations.find((row) => row.id === organizationId) || null, site: sites.find((row) => row.id === siteId) || null, organizationId, siteId, setOrganizationId, setSiteId, loading, refresh }), [organizations, sites, organizationId, siteId, loading]);
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error('useWorkspace must be used inside WorkspaceProvider');
  return value;
}
