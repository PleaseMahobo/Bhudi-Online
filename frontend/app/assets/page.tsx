'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import ModuleShell from '@/shared/components/ModuleShell';
import { useRouter } from 'next/navigation';
import {
  listAssets,
  createAsset,
  updateAsset,
  deleteAsset,
  changeAssetStatus,
  ensureAssetQr,
  getAssetWarranty,
  getAssetDepreciation,
  listAssetLifecycle,
  listVendors,
  createVendor,
  deleteVendor,
  listLicenses,
  createLicense,
  deleteLicense,
  listContracts,
  createContract,
  deleteContract,
  listTicketsForAsset,
  createTicketForAsset,
  type Asset,
  type Vendor,
  type License,
  type Contract,
  type LifecycleEvent,
  type WarrantyInfo,
  type DepreciationInfo,
  type ServiceTicket,
} from '@/lib/api';
import {
  Package,
  Plus,
  Trash2,
  ArrowLeft,
  Save,
  X,
  QrCode,
  Shield,
  FileText,
  Building2,
  RefreshCw,
  Ticket,
} from 'lucide-react';

type Tab = 'assets' | 'vendors' | 'licenses' | 'contracts';

const STATUSES = ['ordered', 'in_stock', 'deployed', 'in_repair', 'retired', 'disposed'];

const emptyAsset = {
  name: '',
  asset_tag: '',
  serial_number: '',
  asset_type: 'hardware',
  manufacturer: '',
  model: '',
  status: 'in_stock',
  location: '',
  assigned_to: '',
  purchase_cost: '' as string | number,
  purchase_date: '',
  warranty_end: '',
  notes: '',
};

const emptyVendor = { name: '', contact_email: '', contact_phone: '', website: '', notes: '' };
const emptyLicense = {
  name: '',
  seats_total: 1,
  seats_used: 0,
  license_key: '',
  expires_at: '',
  notes: '',
};
const emptyContract = {
  name: '',
  contract_type: 'support',
  status: 'active',
  start_date: '',
  end_date: '',
  value: '' as string | number,
  notes: '',
};

function statusColor(status: string) {
  switch (status) {
    case 'deployed':
      return 'bg-emerald-900/60 text-emerald-400';
    case 'in_repair':
      return 'bg-amber-900/60 text-amber-400';
    case 'in_stock':
      return 'bg-sky-900/60 text-sky-400';
    case 'ordered':
      return 'bg-indigo-900/60 text-indigo-300';
    case 'retired':
    case 'disposed':
      return 'bg-zinc-700 text-zinc-400';
    default:
      return 'bg-zinc-700 text-zinc-300';
  }
}

export default function AssetsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>('assets');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [licenses, setLicenses] = useState<License[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [showAssetForm, setShowAssetForm] = useState(false);
  const [showVendorForm, setShowVendorForm] = useState(false);
  const [showLicenseForm, setShowLicenseForm] = useState(false);
  const [showContractForm, setShowContractForm] = useState(false);
  const [editingAssetId, setEditingAssetId] = useState<string | null>(null);

  const [assetForm, setAssetForm] = useState({ ...emptyAsset });
  const [vendorForm, setVendorForm] = useState({ ...emptyVendor });
  const [licenseForm, setLicenseForm] = useState({ ...emptyLicense });
  const [contractForm, setContractForm] = useState({ ...emptyContract });

  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [lifecycle, setLifecycle] = useState<LifecycleEvent[]>([]);
  const [warranty, setWarranty] = useState<WarrantyInfo | null>(null);
  const [depreciation, setDepreciation] = useState<DepreciationInfo | null>(null);
  const [assetTickets, setAssetTickets] = useState<ServiceTicket[]>([]);

  const flash = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 2500);
  };

  const loadData = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [a, v, l, c] = await Promise.all([
        listAssets(),
        listVendors(),
        listLicenses(),
        listContracts(),
      ]);
      setAssets(a);
      setVendors(v);
      setLicenses(l);
      setContracts(c);
    } catch (e: any) {
      setError(e?.message || 'Failed to load asset data');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [loading, user, router]);

  useEffect(() => {
    if (!loading && user) loadData();
  }, [loading, user, loadData]);

  const openCreateAsset = () => {
    setEditingAssetId(null);
    setAssetForm({ ...emptyAsset });
    setShowAssetForm(true);
  };

  const openEditAsset = (asset: Asset) => {
    setEditingAssetId(asset.id);
    setAssetForm({
      name: asset.name || '',
      asset_tag: asset.asset_tag || '',
      serial_number: asset.serial_number || '',
      asset_type: asset.asset_type || 'hardware',
      manufacturer: asset.manufacturer || '',
      model: asset.model || '',
      status: asset.status || 'in_stock',
      location: asset.location || '',
      assigned_to: asset.assigned_to || '',
      purchase_cost: asset.purchase_cost ?? '',
      purchase_date: asset.purchase_date ? asset.purchase_date.slice(0, 10) : '',
      warranty_end: asset.warranty_end ? asset.warranty_end.slice(0, 10) : '',
      notes: asset.notes || '',
    });
    setShowAssetForm(true);
  };

  const saveAsset = async () => {
    try {
      setBusy(true);
      setError(null);
      const payload = {
        name: assetForm.name,
        asset_tag: assetForm.asset_tag || null,
        serial_number: assetForm.serial_number || null,
        asset_type: assetForm.asset_type || null,
        manufacturer: assetForm.manufacturer || null,
        model: assetForm.model || null,
        status: assetForm.status,
        location: assetForm.location || null,
        assigned_to: assetForm.assigned_to || null,
        purchase_cost:
          assetForm.purchase_cost === '' ? null : Number(assetForm.purchase_cost),
        purchase_date: assetForm.purchase_date || null,
        warranty_end: assetForm.warranty_end || null,
        notes: assetForm.notes || null,
      };
      if (editingAssetId) {
        await updateAsset(editingAssetId, payload);
        flash('Asset updated');
      } else {
        await createAsset(payload);
        flash('Asset created');
      }
      setShowAssetForm(false);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to save asset');
    } finally {
      setBusy(false);
    }
  };

  const removeAsset = async (id: string) => {
    if (!confirm('Delete this asset?')) return;
    try {
      await deleteAsset(id);
      flash('Asset deleted');
      if (selectedAsset?.id === id) setSelectedAsset(null);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to delete asset');
    }
  };

  const selectAsset = async (asset: Asset) => {
    setSelectedAsset(asset);
    setWarranty(null);
    setDepreciation(null);
    setLifecycle([]);
    setAssetTickets([]);
    try {
      const [lc, war, dep, tix] = await Promise.all([
        listAssetLifecycle(asset.id),
        getAssetWarranty(asset.id).catch(() => null),
        getAssetDepreciation(asset.id).catch(() => null),
        listTicketsForAsset(asset.id).catch(() => []),
      ]);
      setLifecycle(lc);
      setWarranty(war);
      setDepreciation(dep);
      setAssetTickets(tix);
    } catch (e: any) {
      setError(e?.message || 'Failed to load asset detail');
    }
  };

  const onStatusChange = async (asset: Asset, status: string) => {
    try {
      setBusy(true);
      const updated = await changeAssetStatus(asset.id, status);
      flash(`Status → ${status}`);
      await loadData();
      await selectAsset(updated);
    } catch (e: any) {
      setError(e?.message || 'Failed to change status');
    } finally {
      setBusy(false);
    }
  };

  const onEnsureQr = async (asset: Asset) => {
    try {
      const res = await ensureAssetQr(asset.id);
      flash(`QR: ${res.qr_code}`);
      await loadData();
      if (selectedAsset?.id === asset.id) {
        await selectAsset({ ...asset, qr_code: res.qr_code });
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to generate QR');
    }
  };

  const openTicketForAsset = async (asset: Asset) => {
    try {
      setBusy(true);
      const ticket = await createTicketForAsset(asset.id, {
        title: `Service request for ${asset.name}`,
        description: `Auto-linked ticket for asset ${asset.asset_tag || asset.name}`,
        ticket_type: 'service_request',
        priority: 'medium',
      });
      flash(`Ticket ${ticket.number} created`);
      await selectAsset(asset);
    } catch (e: any) {
      setError(e?.message || 'Failed to create ticket');
    } finally {
      setBusy(false);
    }
  };

  const saveVendor = async () => {
    try {
      setBusy(true);
      await createVendor({
        name: vendorForm.name,
        contact_email: vendorForm.contact_email || null,
        contact_phone: vendorForm.contact_phone || null,
        website: vendorForm.website || null,
        notes: vendorForm.notes || null,
        active: true,
      });
      flash('Vendor created');
      setShowVendorForm(false);
      setVendorForm({ ...emptyVendor });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to create vendor');
    } finally {
      setBusy(false);
    }
  };

  const saveLicense = async () => {
    try {
      setBusy(true);
      await createLicense({
        name: licenseForm.name,
        seats_total: Number(licenseForm.seats_total) || 1,
        seats_used: Number(licenseForm.seats_used) || 0,
        license_key: licenseForm.license_key || null,
        expires_at: licenseForm.expires_at || null,
        notes: licenseForm.notes || null,
        active: true,
      });
      flash('License created');
      setShowLicenseForm(false);
      setLicenseForm({ ...emptyLicense });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to create license');
    } finally {
      setBusy(false);
    }
  };

  const saveContract = async () => {
    try {
      setBusy(true);
      await createContract({
        name: contractForm.name,
        contract_type: contractForm.contract_type || null,
        status: contractForm.status || 'active',
        start_date: contractForm.start_date || null,
        end_date: contractForm.end_date || null,
        value: contractForm.value === '' ? null : Number(contractForm.value),
        notes: contractForm.notes || null,
      });
      flash('Contract created');
      setShowContractForm(false);
      setContractForm({ ...emptyContract });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to create contract');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <ModuleShell title="Assets">
        <div className="text-slate-500">Loading…</div>
      </ModuleShell>
    );
  }

  return (
    <ModuleShell title="Assets" subtitle="Inventory, vendors, licenses & contracts">
      <div className="space-y-6">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/dashboard')}
              className="p-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                <Package className="text-sky-400" /> Asset Management
              </h1>
              <p className="text-zinc-400 text-sm mt-1">
                Hardware inventory, vendors, licenses, contracts & lifecycle
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadData}
              className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 px-4 py-2.5 rounded-xl text-sm"
            >
              <RefreshCw size={16} /> Refresh
            </button>
            {tab === 'assets' && (
              <button
                onClick={openCreateAsset}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium"
              >
                <Plus size={18} /> New Asset
              </button>
            )}
            {tab === 'vendors' && (
              <button
                onClick={() => setShowVendorForm(true)}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium"
              >
                <Plus size={18} /> New Vendor
              </button>
            )}
            {tab === 'licenses' && (
              <button
                onClick={() => setShowLicenseForm(true)}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium"
              >
                <Plus size={18} /> New License
              </button>
            )}
            {tab === 'contracts' && (
              <button
                onClick={() => setShowContractForm(true)}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium"
              >
                <Plus size={18} /> New Contract
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 rounded-2xl border border-red-500/40 bg-red-950/40 text-red-300 text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 rounded-2xl border border-emerald-500/40 bg-emerald-950/40 text-emerald-300 text-sm">
            {success}
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-6">
          {(
            [
              ['assets', `Assets (${assets.length})`],
              ['vendors', `Vendors (${vendors.length})`],
              ['licenses', `Licenses (${licenses.length})`],
              ['contracts', `Contracts (${contracts.length})`],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition ${
                tab === key
                  ? 'bg-sky-600 text-white'
                  : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            {tab === 'assets' && (
              <>
                {assets.length === 0 && !busy && (
                  <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                    No assets yet. Register your first hardware asset.
                  </div>
                )}
                {assets.map((asset) => (
                  <div
                    key={asset.id}
                    className={`bg-zinc-900 border rounded-3xl p-6 cursor-pointer transition ${
                      selectedAsset?.id === asset.id
                        ? 'border-sky-500'
                        : 'border-zinc-700 hover:border-zinc-500'
                    }`}
                    onClick={() => selectAsset(asset)}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold">{asset.name}</h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(asset.status)}`}>
                            {asset.status}
                          </span>
                          {asset.warranty_active && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-900/50 text-emerald-300">
                              Warranty active
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-3 text-xs text-zinc-400">
                          {asset.asset_tag && <span>Tag: {asset.asset_tag}</span>}
                          {asset.serial_number && <span>S/N: {asset.serial_number}</span>}
                          {asset.manufacturer && <span>{asset.manufacturer}</span>}
                          {asset.model && <span>{asset.model}</span>}
                          {asset.location && <span>📍 {asset.location}</span>}
                          {asset.qr_code && <span className="text-sky-400">QR {asset.qr_code}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <select
                          className="bg-zinc-800 border border-zinc-600 rounded-xl px-3 py-2 text-xs"
                          value={asset.status}
                          onChange={(e) => onStatusChange(asset, e.target.value)}
                        >
                          {STATUSES.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={() => onEnsureQr(asset)}
                          className="p-2 rounded-xl bg-zinc-800 hover:bg-zinc-700"
                          title="Ensure QR"
                        >
                          <QrCode size={18} className="text-sky-400" />
                        </button>
                        <button
                          onClick={() => openEditAsset(asset)}
                          className="px-3 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => removeAsset(asset.id)}
                          className="p-2 rounded-xl bg-zinc-800 hover:bg-red-900/40 text-red-400"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </>
            )}

            {tab === 'vendors' && (
              <>
                {vendors.map((v) => (
                  <div
                    key={v.id}
                    className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex justify-between items-center"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Building2 size={18} className="text-sky-400" />
                        <h3 className="font-semibold">{v.name}</h3>
                      </div>
                      <p className="text-xs text-zinc-400 mt-1">
                        {[v.contact_email, v.contact_phone, v.website].filter(Boolean).join(' · ') ||
                          'No contact info'}
                      </p>
                    </div>
                    <button
                      onClick={async () => {
                        if (!confirm('Delete vendor?')) return;
                        await deleteVendor(v.id);
                        flash('Vendor deleted');
                        loadData();
                      }}
                      className="p-2 rounded-xl bg-zinc-800 hover:bg-red-900/40 text-red-400"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </>
            )}

            {tab === 'licenses' && (
              <>
                {licenses.map((lic) => (
                  <div
                    key={lic.id}
                    className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex justify-between items-center"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Shield size={18} className="text-sky-400" />
                        <h3 className="font-semibold">{lic.name}</h3>
                      </div>
                      <p className="text-xs text-zinc-400 mt-1">
                        Seats {lic.seats_used}/{lic.seats_total}
                        {lic.seats_available != null && ` · available ${lic.seats_available}`}
                        {lic.expires_at && ` · expires ${lic.expires_at.slice(0, 10)}`}
                      </p>
                    </div>
                    <button
                      onClick={async () => {
                        if (!confirm('Delete license?')) return;
                        await deleteLicense(lic.id);
                        flash('License deleted');
                        loadData();
                      }}
                      className="p-2 rounded-xl bg-zinc-800 hover:bg-red-900/40 text-red-400"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </>
            )}

            {tab === 'contracts' && (
              <>
                {contracts.map((c) => (
                  <div
                    key={c.id}
                    className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex justify-between items-center"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <FileText size={18} className="text-sky-400" />
                        <h3 className="font-semibold">{c.name}</h3>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300">
                          {c.status}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 mt-1">
                        {c.contract_type || 'contract'}
                        {c.end_date && ` · ends ${c.end_date.slice(0, 10)}`}
                        {c.value != null && ` · ${c.value}`}
                      </p>
                    </div>
                    <button
                      onClick={async () => {
                        if (!confirm('Delete contract?')) return;
                        await deleteContract(c.id);
                        flash('Contract deleted');
                        loadData();
                      }}
                      className="p-2 rounded-xl bg-zinc-800 hover:bg-red-900/40 text-red-400"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>

          <div className="xl:col-span-1">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 sticky top-8">
              {!selectedAsset ? (
                <p className="text-zinc-500 text-sm text-center py-10">
                  Select an asset to view warranty, depreciation, lifecycle & linked tickets.
                </p>
              ) : (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-lg font-semibold">{selectedAsset.name}</h3>
                    <p className="text-xs text-zinc-400 mt-1">
                      {selectedAsset.asset_tag || selectedAsset.id.slice(0, 8)}
                    </p>
                  </div>

                  {warranty && (
                    <div className="bg-zinc-800/60 rounded-2xl p-4 text-sm">
                      <div className="font-medium mb-1">Warranty</div>
                      <div className="text-zinc-400 text-xs space-y-1">
                        <div>Active: {warranty.warranty_active ? 'Yes' : 'No'}</div>
                        {warranty.warranty_end && <div>Ends: {warranty.warranty_end.slice(0, 10)}</div>}
                        {warranty.days_remaining != null && (
                          <div>Days remaining: {warranty.days_remaining}</div>
                        )}
                      </div>
                    </div>
                  )}

                  {depreciation && (
                    <div className="bg-zinc-800/60 rounded-2xl p-4 text-sm">
                      <div className="font-medium mb-1">Depreciation</div>
                      <div className="text-zinc-400 text-xs space-y-1">
                        <div>Method: {depreciation.method}</div>
                        <div>Book value: {depreciation.book_value.toFixed(2)}</div>
                        <div>Accumulated: {depreciation.accumulated_depreciation.toFixed(2)}</div>
                      </div>
                    </div>
                  )}

                  <div>
                    <div className="font-medium text-sm mb-2">Lifecycle</div>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {lifecycle.length === 0 && (
                        <p className="text-xs text-zinc-500">No events yet</p>
                      )}
                      {lifecycle.map((ev) => (
                        <div
                          key={ev.id}
                          className="text-xs bg-zinc-800/50 border border-zinc-700 rounded-xl px-3 py-2"
                        >
                          <span className="text-zinc-400">{ev.from_status || '—'}</span>
                          {' → '}
                          <span className="text-sky-300">{ev.to_status}</span>
                          {ev.reason && <div className="text-zinc-500 mt-0.5">{ev.reason}</div>}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-sm flex items-center gap-2">
                        <Ticket size={14} /> Linked tickets
                      </div>
                      <button
                        onClick={() => openTicketForAsset(selectedAsset)}
                        className="text-xs text-sky-400 hover:text-sky-300"
                      >
                        + Create
                      </button>
                    </div>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {assetTickets.length === 0 && (
                        <p className="text-xs text-zinc-500">No linked tickets</p>
                      )}
                      {assetTickets.map((t) => (
                        <div
                          key={t.id}
                          className="text-xs bg-zinc-800/50 border border-zinc-700 rounded-xl px-3 py-2"
                        >
                          <span className="text-sky-300">{t.number}</span> · {t.status}
                          <div className="text-zinc-400 truncate">{t.title}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {showAssetForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">
                  {editingAssetId ? 'Edit Asset' : 'Create Asset'}
                </h2>
                <button onClick={() => setShowAssetForm(false)} className="p-2 hover:bg-zinc-800 rounded-xl">
                  <X size={20} />
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(
                  [
                    ['name', 'Name *'],
                    ['asset_tag', 'Asset Tag'],
                    ['serial_number', 'Serial Number'],
                    ['asset_type', 'Type'],
                    ['manufacturer', 'Manufacturer'],
                    ['model', 'Model'],
                    ['location', 'Location'],
                    ['assigned_to', 'Assigned To'],
                    ['purchase_cost', 'Purchase Cost'],
                    ['purchase_date', 'Purchase Date'],
                    ['warranty_end', 'Warranty End'],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key}>
                    <label className="text-xs text-zinc-400">{label}</label>
                    <input
                      type={key.includes('date') ? 'date' : key === 'purchase_cost' ? 'number' : 'text'}
                      className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                      value={(assetForm as any)[key]}
                      onChange={(e) => setAssetForm({ ...assetForm, [key]: e.target.value })}
                    />
                  </div>
                ))}
                <div>
                  <label className="text-xs text-zinc-400">Status</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={assetForm.status}
                    onChange={(e) => setAssetForm({ ...assetForm, status: e.target.value })}
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-zinc-400">Notes</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={assetForm.notes}
                    onChange={(e) => setAssetForm({ ...assetForm, notes: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowAssetForm(false)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={saveAsset}
                  disabled={!assetForm.name || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Save Asset
                </button>
              </div>
            </div>
          </div>
        )}

        {showVendorForm && (
          <Modal title="New Vendor" onClose={() => setShowVendorForm(false)}>
            {(['name', 'contact_email', 'contact_phone', 'website', 'notes'] as const).map((k) => (
              <div key={k} className="mb-3">
                <label className="text-xs text-zinc-400 capitalize">{k.replace('_', ' ')}</label>
                <input
                  className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                  value={vendorForm[k]}
                  onChange={(e) => setVendorForm({ ...vendorForm, [k]: e.target.value })}
                />
              </div>
            ))}
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowVendorForm(false)} className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm">
                Cancel
              </button>
              <button
                onClick={saveVendor}
                disabled={!vendorForm.name || busy}
                className="px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </Modal>
        )}

        {showLicenseForm && (
          <Modal title="New License" onClose={() => setShowLicenseForm(false)}>
            <div className="mb-3">
              <label className="text-xs text-zinc-400">Name</label>
              <input
                className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                value={licenseForm.name}
                onChange={(e) => setLicenseForm({ ...licenseForm, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-xs text-zinc-400">Seats total</label>
                <input
                  type="number"
                  className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                  value={licenseForm.seats_total}
                  onChange={(e) =>
                    setLicenseForm({ ...licenseForm, seats_total: Number(e.target.value) })
                  }
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400">Seats used</label>
                <input
                  type="number"
                  className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                  value={licenseForm.seats_used}
                  onChange={(e) =>
                    setLicenseForm({ ...licenseForm, seats_used: Number(e.target.value) })
                  }
                />
              </div>
            </div>
            <div className="mb-3">
              <label className="text-xs text-zinc-400">Expires</label>
              <input
                type="date"
                className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                value={licenseForm.expires_at}
                onChange={(e) => setLicenseForm({ ...licenseForm, expires_at: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowLicenseForm(false)} className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm">
                Cancel
              </button>
              <button
                onClick={saveLicense}
                disabled={!licenseForm.name || busy}
                className="px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </Modal>
        )}

        {showContractForm && (
          <Modal title="New Contract" onClose={() => setShowContractForm(false)}>
            <div className="mb-3">
              <label className="text-xs text-zinc-400">Name</label>
              <input
                className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                value={contractForm.name}
                onChange={(e) => setContractForm({ ...contractForm, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-xs text-zinc-400">Type</label>
                <input
                  className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                  value={contractForm.contract_type}
                  onChange={(e) =>
                    setContractForm({ ...contractForm, contract_type: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400">Status</label>
                <input
                  className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                  value={contractForm.status}
                  onChange={(e) => setContractForm({ ...contractForm, status: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-xs text-zinc-400">Start</label>
                <input
                  type="date"
                  className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                  value={contractForm.start_date}
                  onChange={(e) => setContractForm({ ...contractForm, start_date: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400">End</label>
                <input
                  type="date"
                  className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                  value={contractForm.end_date}
                  onChange={(e) => setContractForm({ ...contractForm, end_date: e.target.value })}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowContractForm(false)} className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm">
                Cancel
              </button>
              <button
                onClick={saveContract}
                disabled={!contractForm.name || busy}
                className="px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </Modal>
        )}
      </div>
    </ModuleShell>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">{title}</h2>
          <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-xl">
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
