'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  createOrganization,
  listBillingPlans,
  listContacts,
  listOrganizations,
  listSites,
  listTechnicians,
  seedBillingPlans,
} from '@/lib/api-modules';

export default function MspPage() {
  const [orgs, setOrgs] = useState<any[]>([]);
  const [sites, setSites] = useState<any[]>([]);
  const [techs, setTechs] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');

  const load = useCallback(async () => {
    setError(null);
    try {
      const [o, s, t, c, p] = await Promise.all([
        listOrganizations(),
        listSites(),
        listTechnicians(),
        listContacts(),
        listBillingPlans(),
      ]);
      setOrgs(o);
      setSites(s);
      setTechs(t);
      setContacts(c);
      setPlans(p);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCreateOrg = async () => {
    if (!name.trim()) return;
    try {
      await createOrganization({ name: name.trim(), org_type: 'client', status: 'active' });
      setName('');
      await load();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  return (
    <ModuleShell title="MSP Multi-Tenant" subtitle="Organizations, sites, technicians, billing plans">
      <Err error={error} />

      <Panel
        title="Organizations"
        actions={
          <div className="flex gap-2">
            <input
              className="bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-sm"
              placeholder="New org name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Btn onClick={onCreateOrg}>Create</Btn>
            <Btn variant="ghost" onClick={load}>
              Refresh
            </Btn>
          </div>
        }
      >
        <DataTable
          columns={["Name", "Type", "Status", "ID"]}
          rows={orgs.map((o) => [o.name, o.org_type, o.status, o.id])}
        />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Sites">
          <DataTable
            columns={["Name", "Org", "City"]}
            rows={sites.map((s) => [s.name, s.organization_id, s.city])}
          />
        </Panel>
        <Panel title="Technicians">
          <DataTable
            columns={["Name", "Email", "Status"]}
            rows={techs.map((t) => [t.display_name || t.name, t.email, t.status])}
          />
        </Panel>
        <Panel title="Contacts">
          <DataTable
            columns={["Name", "Email", "Type"]}
            rows={contacts.map((c) => [c.name, c.email, c.contact_type])}
          />
        </Panel>
        <Panel
          title="Billing plans"
          actions={
            <Btn variant="ghost" onClick={() => seedBillingPlans().then(load).catch((e) => setError(e.message))}>
              Seed defaults
            </Btn>
          }
        >
          <DataTable
            columns={["Code", "Name", "Price"]}
            rows={plans.map((p) => [p.code, p.name, p.price_monthly ?? p.unit_amount])}
          />
        </Panel>
      </div>
    </ModuleShell>
  );
}
