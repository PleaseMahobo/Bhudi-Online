'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  createCustomerWizard,
  deleteOrganization,
  inviteUser,
  listBillingPlans,
  listContacts,
  listOrganizations,
  listSites,
  listTechnicians,
  seedBillingPlans,
} from '@/lib/api-modules';

const inputCls =
  'w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400';

const ROLES = ['viewer', 'technician', 'manager', 'admin', 'customer', 'system_admin'] as const;

export default function MspPage() {
  const [orgs, setOrgs] = useState<any[]>([]);
  const [sites, setSites] = useState<any[]>([]);
  const [techs, setTechs] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Wizard form
  const [wiz, setWiz] = useState({
    name: '',
    email: '',
    phone: '',
    siteName: 'HQ',
    siteCity: '',
    contactFirst: '',
    contactLast: '',
    contactEmail: '',
    contactPhone: '',
  });

  // Invite form
  const [invite, setInvite] = useState({
    email: '',
    role: 'viewer',
    tenant_id: '',
    first_name: '',
    last_name: '',
  });
  const [lastTempPassword, setLastTempPassword] = useState<string | null>(null);

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
      if (!invite.tenant_id && o.length) {
        setInvite((prev) => ({ ...prev, tenant_id: o[0].tenant_id }));
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, [invite.tenant_id]);

  useEffect(() => {
    load();
  }, [load]);

  const onWizardSubmit = async () => {
    if (!wiz.name.trim() || !wiz.siteName.trim() || !wiz.contactFirst.trim()) {
      setError('Customer name, site name, and contact first name are required.');
      return;
    }
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const result = await createCustomerWizard({
        name: wiz.name.trim(),
        org_type: 'client',
        status: 'active',
        email: wiz.email.trim() || null,
        phone: wiz.phone.trim() || null,
        site: {
          name: wiz.siteName.trim(),
          city: wiz.siteCity.trim() || null,
        },
        contact: {
          first_name: wiz.contactFirst.trim(),
          last_name: wiz.contactLast.trim() || null,
          email: wiz.contactEmail.trim() || null,
          phone: wiz.contactPhone.trim() || null,
        },
      });
      setInfo(
        `Created customer “${result.organization.name}” (tenant ${result.organization.tenant_id}). Site + primary contact added.`
      );
      setWiz({
        name: '',
        email: '',
        phone: '',
        siteName: 'HQ',
        siteCity: '',
        contactFirst: '',
        contactLast: '',
        contactEmail: '',
        contactPhone: '',
      });
      setInvite((prev) => ({ ...prev, tenant_id: result.organization.tenant_id }));
      await load();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const onDeleteOrg = async (org: any) => {
    if (!confirm(`Delete organization “${org.name}”? This cannot be undone.`)) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await deleteOrganization(org.id);
      setInfo(`Deleted organization “${org.name}”.`);
      await load();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const onInvite = async () => {
    if (!invite.email.trim() || !invite.tenant_id) {
      setError('Invite requires email and a tenant.');
      return;
    }
    setBusy(true);
    setError(null);
    setInfo(null);
    setLastTempPassword(null);
    try {
      const res = await inviteUser({
        email: invite.email.trim(),
        role: invite.role,
        tenant_id: invite.tenant_id,
        first_name: invite.first_name.trim() || undefined,
        last_name: invite.last_name.trim() || undefined,
      });
      setLastTempPassword(res.temporary_password);
      setInfo(
        `Invited ${res.email} as ${res.role} on tenant ${res.tenant_id}. Copy the temporary password below.`
      );
      setInvite((prev) => ({ ...prev, email: '', first_name: '', last_name: '' }));
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleShell
      title="Customers"
      subtitle="Create customers, invite users with roles, and manage organizations"
      breadcrumbs={[{ label: 'Customers' }]}
    >
      <Err error={error} />
      {info && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {info}
        </div>
      )}

      <Panel title="New customer wizard">
        <p className="mb-4 text-sm text-slate-500">
          Creates organization, default site, and primary contact in one step. A tenant is auto-created for agent
          enrollment.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Organization</p>
            <input
              className={inputCls}
              placeholder="Customer name *"
              value={wiz.name}
              onChange={(e) => setWiz({ ...wiz, name: e.target.value })}
            />
            <input
              className={inputCls}
              placeholder="Company email"
              value={wiz.email}
              onChange={(e) => setWiz({ ...wiz, email: e.target.value })}
            />
            <input
              className={inputCls}
              placeholder="Phone"
              value={wiz.phone}
              onChange={(e) => setWiz({ ...wiz, phone: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Site</p>
            <input
              className={inputCls}
              placeholder="Site name *"
              value={wiz.siteName}
              onChange={(e) => setWiz({ ...wiz, siteName: e.target.value })}
            />
            <input
              className={inputCls}
              placeholder="City"
              value={wiz.siteCity}
              onChange={(e) => setWiz({ ...wiz, siteCity: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Primary contact</p>
            <input
              className={inputCls}
              placeholder="First name *"
              value={wiz.contactFirst}
              onChange={(e) => setWiz({ ...wiz, contactFirst: e.target.value })}
            />
            <input
              className={inputCls}
              placeholder="Last name"
              value={wiz.contactLast}
              onChange={(e) => setWiz({ ...wiz, contactLast: e.target.value })}
            />
            <input
              className={inputCls}
              placeholder="Email"
              value={wiz.contactEmail}
              onChange={(e) => setWiz({ ...wiz, contactEmail: e.target.value })}
            />
            <input
              className={inputCls}
              placeholder="Phone"
              value={wiz.contactPhone}
              onChange={(e) => setWiz({ ...wiz, contactPhone: e.target.value })}
            />
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <Btn onClick={onWizardSubmit}>{busy ? 'Working…' : 'Create customer'}</Btn>
          <Btn variant="ghost" onClick={load}>
            Refresh
          </Btn>
        </div>
      </Panel>

      <Panel title="Invite user (credentials + rights)">
        <p className="mb-4 text-sm text-slate-500">
          Binds a portal user to a customer tenant and RBAC role. User signs in with Supabase using the same email;
          Bhudi maps identity and applies tenant + role.
        </p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          <input
            className={inputCls}
            placeholder="Email *"
            value={invite.email}
            onChange={(e) => setInvite({ ...invite, email: e.target.value })}
          />
          <select
            className={inputCls}
            value={invite.role}
            onChange={(e) => setInvite({ ...invite, role: e.target.value })}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <select
            className={inputCls}
            value={invite.tenant_id}
            onChange={(e) => setInvite({ ...invite, tenant_id: e.target.value })}
          >
            <option value="">Select customer tenant *</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.tenant_id}>
                {o.name} ({String(o.tenant_id).slice(0, 8)}…)
              </option>
            ))}
          </select>
          <input
            className={inputCls}
            placeholder="First name"
            value={invite.first_name}
            onChange={(e) => setInvite({ ...invite, first_name: e.target.value })}
          />
          <input
            className={inputCls}
            placeholder="Last name"
            value={invite.last_name}
            onChange={(e) => setInvite({ ...invite, last_name: e.target.value })}
          />
        </div>
        <div className="mt-4">
          <Btn onClick={onInvite}>{busy ? 'Working…' : 'Invite user'}</Btn>
        </div>
        {lastTempPassword && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <p className="font-semibold">Temporary password (copy now — shown once)</p>
            <code className="mt-1 block break-all font-mono text-base">{lastTempPassword}</code>
          </div>
        )}
      </Panel>

      <Panel title="Organizations">
        {orgs.length === 0 ? (
          <p className="text-sm text-slate-500">No organizations yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Type</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium">Tenant</th>
                  <th className="py-2 pr-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orgs.map((o) => (
                  <tr key={o.id} className="border-b border-slate-100 text-slate-700">
                    <td className="py-2.5 pr-4 font-medium">{o.name}</td>
                    <td className="py-2.5 pr-4">{o.org_type}</td>
                    <td className="py-2.5 pr-4">{o.status}</td>
                    <td className="max-w-[12rem] truncate py-2.5 pr-4 font-mono text-xs">{o.tenant_id}</td>
                    <td className="py-2.5 pr-4">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => onDeleteOrg(o)}
                        className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Sites">
          <DataTable
            columns={['Name', 'Org', 'City']}
            rows={sites.map((s) => [s.name, s.organization_id, s.city])}
          />
        </Panel>
        <Panel title="Technicians">
          <DataTable
            columns={['Name', 'Email', 'Status']}
            rows={techs.map((t) => [t.display_name || t.name, t.email, t.status])}
          />
        </Panel>
        <Panel title="Contacts">
          <DataTable
            columns={['Name', 'Email', 'Type']}
            rows={contacts.map((c) => [
              [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name,
              c.email,
              c.contact_type,
            ])}
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
            columns={['Code', 'Name', 'Price']}
            rows={plans.map((p) => [p.code, p.name, p.price_monthly ?? p.price ?? p.unit_amount])}
          />
        </Panel>
      </div>
    </ModuleShell>
  );
}
