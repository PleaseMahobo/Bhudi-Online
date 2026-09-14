'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ModuleShell, { Btn, DataTable, Err, Panel } from '@/shared/components/ModuleShell';
import {
  createCustomerWizard,
  deleteOrganization,
  getCustomerDetail,
  getCustomersOverview,
  inviteUser,
  listBillingPlans,
  seedBillingPlans,
  type CustomerDetail,
  type CustomerOverviewRow,
} from '@/lib/api-modules';

const inputCls =
  'w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400';

const ROLES = ['viewer', 'technician', 'manager', 'admin', 'customer', 'system_admin'] as const;

type Tab = 'directory' | 'wizard' | 'invite';
type DetailTab = 'overview' | 'sites' | 'users' | 'devices';

function statusBadge(status?: string | null) {
  const s = (status || 'unknown').toLowerCase();
  const map: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-800',
    trial: 'bg-sky-100 text-sky-800',
    suspended: 'bg-amber-100 text-amber-800',
    churned: 'bg-red-100 text-red-800',
    online: 'bg-emerald-100 text-emerald-800',
    offline: 'bg-slate-200 text-slate-600',
  };
  return map[s] || 'bg-slate-100 text-slate-700';
}

function roleBadge(role: string) {
  const map: Record<string, string> = {
    system_admin: 'bg-purple-100 text-purple-800',
    admin: 'bg-indigo-100 text-indigo-800',
    manager: 'bg-sky-100 text-sky-800',
    technician: 'bg-amber-100 text-amber-800',
    customer: 'bg-emerald-100 text-emerald-800',
    viewer: 'bg-slate-100 text-slate-700',
  };
  return map[role] || 'bg-slate-100 text-slate-600';
}

function formatAddress(o: {
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
}) {
  const parts = [
    o.address_line1,
    o.address_line2,
    [o.city, o.state].filter(Boolean).join(', '),
    o.postal_code,
    o.country,
  ].filter(Boolean);
  return parts.length ? parts.join(' · ') : '—';
}

function fmtDate(v?: string | null) {
  if (!v) return '—';
  try {
    return new Date(v).toLocaleString();
  } catch {
    return v;
  }
}

export default function MspPage() {
  const [tab, setTab] = useState<Tab>('directory');
  const [customers, setCustomers] = useState<CustomerOverviewRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CustomerDetail | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>('overview');
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [plans, setPlans] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [wiz, setWiz] = useState({
    name: '',
    email: '',
    phone: '',
    address_line1: '',
    city: '',
    state: '',
    postal_code: '',
    country: '',
    siteName: 'HQ',
    siteCity: '',
    contactFirst: '',
    contactLast: '',
    contactEmail: '',
    contactPhone: '',
  });

  const [invite, setInvite] = useState({
    email: '',
    role: 'viewer',
    tenant_id: '',
    first_name: '',
    last_name: '',
  });
  const [lastTempPassword, setLastTempPassword] = useState<string | null>(null);

  const loadDirectory = useCallback(async () => {
    setError(null);
    try {
      const [ov, p] = await Promise.all([
        getCustomersOverview(),
        listBillingPlans().catch(() => []),
      ]);
      setCustomers(ov.customers || []);
      setPlans(p);
      if (!invite.tenant_id && ov.customers?.length) {
        setInvite((prev) => ({ ...prev, tenant_id: ov.customers[0].tenant_id }));
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, [invite.tenant_id]);

  const loadDetail = useCallback(async (orgId: string) => {
    setBusy(true);
    setError(null);
    try {
      const d = await getCustomerDetail(orgId);
      setDetail(d);
      setSelectedId(orgId);
      setDetailTab('overview');
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    loadDirectory();
  }, [loadDirectory]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return customers.filter((c) => {
      if (statusFilter && c.status !== statusFilter) return false;
      if (!q) return true;
      const hay = [
        c.name,
        c.legal_name,
        c.email,
        c.city,
        c.country,
        c.slug,
        c.tenant_id,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [customers, filter, statusFilter]);

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
          city: wiz.siteCity.trim() || wiz.city.trim() || null,
          address_line1: wiz.address_line1.trim() || null,
          state: wiz.state.trim() || null,
          postal_code: wiz.postal_code.trim() || null,
          country: wiz.country.trim() || null,
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
        address_line1: '',
        city: '',
        state: '',
        postal_code: '',
        country: '',
        siteName: 'HQ',
        siteCity: '',
        contactFirst: '',
        contactLast: '',
        contactEmail: '',
        contactPhone: '',
      });
      setInvite((prev) => ({ ...prev, tenant_id: result.organization.tenant_id }));
      setTab('directory');
      await loadDirectory();
      await loadDetail(result.organization.id);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const onDeleteOrg = async (org: CustomerOverviewRow) => {
    if (!confirm(`Delete organization “${org.name}”? This cannot be undone.`)) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await deleteOrganization(org.id);
      setInfo(`Deleted organization “${org.name}”.`);
      if (selectedId === org.id) {
        setSelectedId(null);
        setDetail(null);
      }
      await loadDirectory();
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
      if (selectedId && detail?.organization.tenant_id === invite.tenant_id) {
        await loadDetail(selectedId);
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleShell
      title="Customers"
      subtitle="Directory, addresses, tenants, RBAC roles, and device connection matrix"
      breadcrumbs={[{ label: 'Customers' }]}
    >
      <Err error={error} />
      {info && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {info}
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {(
          [
            ['directory', 'Directory'],
            ['wizard', 'New customer'],
            ['invite', 'Invite user'],
          ] as [Tab, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
              tab === id
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
        <Btn variant="ghost" onClick={loadDirectory}>
          Refresh
        </Btn>
      </div>

      {tab === 'wizard' && (
        <Panel title="New customer wizard">
          <p className="mb-4 text-sm text-slate-500">
            Creates organization, default site, and primary contact. A tenant is auto-created for agent enrollment.
          </p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Organization</p>
              <input className={inputCls} placeholder="Customer name *" value={wiz.name} onChange={(e) => setWiz({ ...wiz, name: e.target.value })} />
              <input className={inputCls} placeholder="Company email" value={wiz.email} onChange={(e) => setWiz({ ...wiz, email: e.target.value })} />
              <input className={inputCls} placeholder="Phone" value={wiz.phone} onChange={(e) => setWiz({ ...wiz, phone: e.target.value })} />
              <input className={inputCls} placeholder="Address line 1" value={wiz.address_line1} onChange={(e) => setWiz({ ...wiz, address_line1: e.target.value })} />
              <div className="grid grid-cols-2 gap-2">
                <input className={inputCls} placeholder="City" value={wiz.city} onChange={(e) => setWiz({ ...wiz, city: e.target.value })} />
                <input className={inputCls} placeholder="State" value={wiz.state} onChange={(e) => setWiz({ ...wiz, state: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input className={inputCls} placeholder="Postal code" value={wiz.postal_code} onChange={(e) => setWiz({ ...wiz, postal_code: e.target.value })} />
                <input className={inputCls} placeholder="Country" value={wiz.country} onChange={(e) => setWiz({ ...wiz, country: e.target.value })} />
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Site</p>
              <input className={inputCls} placeholder="Site name *" value={wiz.siteName} onChange={(e) => setWiz({ ...wiz, siteName: e.target.value })} />
              <input className={inputCls} placeholder="Site city" value={wiz.siteCity} onChange={(e) => setWiz({ ...wiz, siteCity: e.target.value })} />
            </div>
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Primary contact</p>
              <input className={inputCls} placeholder="First name *" value={wiz.contactFirst} onChange={(e) => setWiz({ ...wiz, contactFirst: e.target.value })} />
              <input className={inputCls} placeholder="Last name" value={wiz.contactLast} onChange={(e) => setWiz({ ...wiz, contactLast: e.target.value })} />
              <input className={inputCls} placeholder="Email" value={wiz.contactEmail} onChange={(e) => setWiz({ ...wiz, contactEmail: e.target.value })} />
              <input className={inputCls} placeholder="Phone" value={wiz.contactPhone} onChange={(e) => setWiz({ ...wiz, contactPhone: e.target.value })} />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <Btn onClick={onWizardSubmit}>{busy ? 'Working…' : 'Create customer'}</Btn>
          </div>
        </Panel>
      )}

      {tab === 'invite' && (
        <Panel title="Invite user (credentials + RBAC role)">
          <p className="mb-4 text-sm text-slate-500">
            Binds a portal user to a customer tenant and RBAC role (viewer, technician, manager, admin, customer, system_admin).
          </p>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            <input className={inputCls} placeholder="Email *" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
            <select className={inputCls} value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            <select className={inputCls} value={invite.tenant_id} onChange={(e) => setInvite({ ...invite, tenant_id: e.target.value })}>
              <option value="">Select customer tenant *</option>
              {customers.map((o) => (
                <option key={o.id} value={o.tenant_id}>
                  {o.name} ({String(o.tenant_id).slice(0, 8)}…)
                </option>
              ))}
            </select>
            <input className={inputCls} placeholder="First name" value={invite.first_name} onChange={(e) => setInvite({ ...invite, first_name: e.target.value })} />
            <input className={inputCls} placeholder="Last name" value={invite.last_name} onChange={(e) => setInvite({ ...invite, last_name: e.target.value })} />
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
      )}

      {tab === 'directory' && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
          <div className="xl:col-span-2 space-y-4">
            <Panel title={`Customers (${filtered.length})`}>
              <div className="mb-3 flex flex-wrap gap-2">
                <input
                  className={`${inputCls} max-w-xs`}
                  placeholder="Search name, city, tenant…"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
                <select
                  className={`${inputCls} max-w-[10rem]`}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">All statuses</option>
                  <option value="active">active</option>
                  <option value="trial">trial</option>
                  <option value="suspended">suspended</option>
                  <option value="churned">churned</option>
                </select>
              </div>
              {filtered.length === 0 ? (
                <p className="text-sm text-slate-500">No customers yet. Use New customer to create one.</p>
              ) : (
                <div className="max-h-[70vh] space-y-2 overflow-y-auto">
                  {filtered.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => loadDetail(c.id)}
                      className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                        selectedId === c.id
                          ? 'border-indigo-300 bg-indigo-50'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-semibold text-slate-800">{c.name}</div>
                          <div className="mt-0.5 text-xs text-slate-500">{formatAddress(c)}</div>
                          <div className="mt-1 font-mono text-[11px] text-slate-400">
                            tenant {String(c.tenant_id).slice(0, 13)}…
                          </div>
                        </div>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge(c.status)}`}>
                          {c.status}
                        </span>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
                        <span>{c.counts.users} users</span>
                        <span>·</span>
                        <span>
                          {c.counts.devices_online}/{c.counts.devices} devices online
                        </span>
                        <span>·</span>
                        <span>{c.counts.sites} sites</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </Panel>

            <Panel
              title="Billing plans"
              actions={
                <Btn variant="ghost" onClick={() => seedBillingPlans().then(loadDirectory).catch((e) => setError(e.message))}>
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

          <div className="xl:col-span-3">
            {!detail ? (
              <Panel title="Customer detail">
                <p className="text-sm text-slate-500">Select a customer from the directory to view full details, RBAC, and device connections.</p>
              </Panel>
            ) : (
              <div className="space-y-4">
                <Panel
                  title={detail.organization.name}
                  actions={
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onDeleteOrg(detail.organization)}
                      className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  }
                >
                  <div className="flex flex-wrap items-center gap-2 mb-4">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge(detail.organization.status)}`}>
                      {detail.organization.status}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
                      {detail.organization.org_type}
                    </span>
                    <span className="font-mono text-xs text-slate-400">
                      tenant {detail.organization.tenant_id}
                    </span>
                  </div>

                  <div className="mb-4 flex flex-wrap gap-2">
                    {(
                      [
                        ['overview', 'Overview'],
                        ['sites', `Sites & contacts (${detail.sites.length}/${detail.contacts.length})`],
                        ['users', `Users & RBAC (${detail.users.length})`],
                        ['devices', `Devices (${detail.devices.length})`],
                      ] as [DetailTab, string][]
                    ).map(([id, label]) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setDetailTab(id)}
                        className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                          detailTab === id
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {detailTab === 'overview' && (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 text-sm">
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Address</h4>
                        <p className="text-slate-700">{formatAddress(detail.organization)}</p>
                        <p className="text-slate-500">Timezone: {detail.organization.timezone || '—'}</p>
                      </div>
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Contact</h4>
                        <p className="text-slate-700">{detail.organization.email || '—'}</p>
                        <p className="text-slate-700">{detail.organization.phone || '—'}</p>
                        <p className="text-slate-700">{detail.organization.website || '—'}</p>
                      </div>
                      <div className="md:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {[
                          ['Users', detail.organization.counts.users],
                          ['Devices', detail.organization.counts.devices],
                          ['Online', detail.organization.counts.devices_online],
                          ['Sites', detail.organization.counts.sites],
                        ].map(([label, n]) => (
                          <div key={String(label)} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                            <div className="text-[11px] text-slate-500">{label}</div>
                            <div className="text-lg font-semibold text-slate-800">{n}</div>
                          </div>
                        ))}
                      </div>
                      {detail.organization.notes && (
                        <div className="md:col-span-2">
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Notes</h4>
                          <p className="mt-1 text-slate-600">{detail.organization.notes}</p>
                        </div>
                      )}
                      <div className="md:col-span-2 text-xs text-slate-400">
                        Created {fmtDate(detail.organization.created_at)} · Updated {fmtDate(detail.organization.updated_at)}
                        {detail.isolation?.subscription_status && (
                          <> · Subscription: {detail.isolation.subscription_status}</>
                        )}
                      </div>
                    </div>
                  )}

                  {detailTab === 'sites' && (
                    <div className="space-y-6">
                      <div>
                        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Sites</h4>
                        {detail.sites.length === 0 ? (
                          <p className="text-sm text-slate-500">No sites.</p>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-200 text-left text-slate-500">
                                  <th className="py-2 pr-3 font-medium">Name</th>
                                  <th className="py-2 pr-3 font-medium">Address</th>
                                  <th className="py-2 pr-3 font-medium">Phone</th>
                                  <th className="py-2 pr-3 font-medium">Enabled</th>
                                </tr>
                              </thead>
                              <tbody>
                                {detail.sites.map((s) => (
                                  <tr key={s.id} className="border-b border-slate-100">
                                    <td className="py-2 pr-3 font-medium">{s.name}</td>
                                    <td className="py-2 pr-3 text-slate-600">{formatAddress(s)}</td>
                                    <td className="py-2 pr-3">{s.phone || '—'}</td>
                                    <td className="py-2 pr-3">{s.enabled ? 'yes' : 'no'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                      <div>
                        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Contacts</h4>
                        {detail.contacts.length === 0 ? (
                          <p className="text-sm text-slate-500">No contacts.</p>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-200 text-left text-slate-500">
                                  <th className="py-2 pr-3 font-medium">Name</th>
                                  <th className="py-2 pr-3 font-medium">Email</th>
                                  <th className="py-2 pr-3 font-medium">Phone</th>
                                  <th className="py-2 pr-3 font-medium">Type</th>
                                  <th className="py-2 pr-3 font-medium">Primary</th>
                                </tr>
                              </thead>
                              <tbody>
                                {detail.contacts.map((c) => (
                                  <tr key={c.id} className="border-b border-slate-100">
                                    <td className="py-2 pr-3 font-medium">
                                      {[c.first_name, c.last_name].filter(Boolean).join(' ')}
                                    </td>
                                    <td className="py-2 pr-3">{c.email || '—'}</td>
                                    <td className="py-2 pr-3">{c.phone || c.mobile || '—'}</td>
                                    <td className="py-2 pr-3">{c.contact_type}</td>
                                    <td className="py-2 pr-3">{c.is_primary ? 'yes' : '—'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                      {detail.technicians.length > 0 && (
                        <div>
                          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Technicians</h4>
                          <DataTable
                            columns={['Name', 'Email', 'Role', 'Status']}
                            rows={detail.technicians.map((t) => [
                              t.display_name,
                              t.email,
                              t.role_name,
                              t.status,
                            ])}
                          />
                        </div>
                      )}
                    </div>
                  )}

                  {detailTab === 'users' && (
                    <div>
                      <p className="mb-3 text-sm text-slate-500">
                        Portal users bound to this tenant, with primary role and RBAC role assignments.
                      </p>
                      {detail.users.length === 0 ? (
                        <p className="text-sm text-slate-500">
                          No users yet.{' '}
                          <button type="button" className="text-indigo-600 underline" onClick={() => setTab('invite')}>
                            Invite a user
                          </button>
                        </p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-slate-200 text-left text-slate-500">
                                <th className="py-2 pr-3 font-medium">User</th>
                                <th className="py-2 pr-3 font-medium">Primary role</th>
                                <th className="py-2 pr-3 font-medium">RBAC roles</th>
                                <th className="py-2 pr-3 font-medium">Active</th>
                                <th className="py-2 pr-3 font-medium">MFA</th>
                                <th className="py-2 pr-3 font-medium">Last login</th>
                              </tr>
                            </thead>
                            <tbody>
                              {detail.users.map((u) => (
                                <tr key={u.id} className="border-b border-slate-100">
                                  <td className="py-2.5 pr-3">
                                    <div className="font-medium text-slate-800">{u.email}</div>
                                    <div className="text-xs text-slate-500">
                                      {[u.first_name, u.last_name].filter(Boolean).join(' ') || '—'}
                                    </div>
                                  </td>
                                  <td className="py-2.5 pr-3">
                                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${roleBadge(u.role)}`}>
                                      {u.role}
                                    </span>
                                  </td>
                                  <td className="py-2.5 pr-3">
                                    <div className="flex flex-wrap gap-1">
                                      {(u.roles || []).map((r) => (
                                        <span key={r} className={`rounded-full px-2 py-0.5 text-xs ${roleBadge(r)}`}>
                                          {r}
                                        </span>
                                      ))}
                                    </div>
                                  </td>
                                  <td className="py-2.5 pr-3">{u.active ? 'yes' : 'no'}</td>
                                  <td className="py-2.5 pr-3">{u.mfa_enabled ? 'on' : 'off'}</td>
                                  <td className="py-2.5 pr-3 text-xs text-slate-500">{fmtDate(u.last_login_at)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}

                  {detailTab === 'devices' && (
                    <div>
                      <p className="mb-3 text-sm text-slate-500">
                        Device connection matrix for this tenant — when agents enrolled, last seen, and how they connected.
                      </p>
                      {detail.devices.length === 0 ? (
                        <p className="text-sm text-slate-500">No devices enrolled under this tenant yet.</p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-slate-200 text-left text-slate-500">
                                <th className="py-2 pr-3 font-medium">Hostname</th>
                                <th className="py-2 pr-3 font-medium">Status</th>
                                <th className="py-2 pr-3 font-medium">IP</th>
                                <th className="py-2 pr-3 font-medium">OS</th>
                                <th className="py-2 pr-3 font-medium">Agent</th>
                                <th className="py-2 pr-3 font-medium">Via</th>
                                <th className="py-2 pr-3 font-medium">Last seen</th>
                                <th className="py-2 pr-3 font-medium">Enrolled</th>
                              </tr>
                            </thead>
                            <tbody>
                              {detail.devices.map((d) => (
                                <tr key={d.id} className="border-b border-slate-100">
                                  <td className="py-2.5 pr-3 font-medium">{d.hostname || d.id.slice(0, 8)}</td>
                                  <td className="py-2.5 pr-3">
                                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge(d.status)}`}>
                                      {d.status || 'unknown'}
                                    </span>
                                  </td>
                                  <td className="py-2.5 pr-3 font-mono text-xs">{d.ip || '—'}</td>
                                  <td className="py-2.5 pr-3">{d.os || '—'}</td>
                                  <td className="py-2.5 pr-3 text-xs">{d.agent_version || '—'}</td>
                                  <td className="py-2.5 pr-3 text-xs">{d.connected_via || '—'}</td>
                                  <td className="py-2.5 pr-3 text-xs text-slate-500">{fmtDate(d.last_seen)}</td>
                                  <td className="py-2.5 pr-3 text-xs text-slate-500">{fmtDate(d.created_at)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </Panel>
              </div>
            )}
          </div>
        </div>
      )}
    </ModuleShell>
  );
}
