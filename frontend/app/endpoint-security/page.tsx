'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import ModuleShell from '@/shared/components/ModuleShell';
import { useRouter } from 'next/navigation';
import {
  listSecurityProviders,
  seedSecurityProviders,
  updateSecurityProvider,
  listSecurityAgents,
  createSecurityAgent,
  listSecurityFindings,
  updateSecurityFinding,
  createSecurityFinding,
  getOrgSecurityScore,
  listSecurityScores,
  recomputeAllSecurityScores,
  getSecurityMatrix,
  listSecurityConnectors,
  syncSecurityProvider,
  syncAllSecurityProviders,
  getDevices,
  type SecurityProvider,
  type EndpointSecurityAgent,
  type SecurityFinding,
  type EndpointSecurityScore,
  type OrgSecurityScore,
  type SecurityMatrixRow,
  type SecurityMatrixResponse,
  type Device,
} from '@/lib/api';
import {
  Shield,
  ArrowLeft,
  RefreshCw,
  Plus,
  X,
  Save,
  CheckCircle2,
  AlertTriangle,
  Server,
  Activity,
  Cloud,
  Filter,
  Table2,
} from 'lucide-react';

type Tab = 'matrix' | 'overview' | 'providers' | 'agents' | 'findings' | 'scores';

const CLOUD_CONNECTOR_KEYS = new Set([
  'crowdstrike',
  'sentinelone',
  'huntress',
  'bitdefender',
  'sophos',
  'microsoft_defender_xdr',
]);

const CONFIG_HINTS: Record<string, string[]> = {
  crowdstrike: ['client_id', 'client_secret', 'base_url (optional)'],
  sentinelone: ['api_token', 'base_url'],
  huntress: ['api_key', 'api_secret'],
  bitdefender: ['api_key', 'company_id (optional)'],
  sophos: ['client_id', 'client_secret', 'tenant_id', 'data_region'],
  microsoft_defender_xdr: ['tenant_id', 'client_id', 'client_secret'],
};

function gradeColor(grade: string) {
  switch (grade) {
    case 'A':
      return 'text-emerald-300 bg-emerald-900/50';
    case 'B':
      return 'text-sky-300 bg-sky-900/50';
    case 'C':
      return 'text-amber-300 bg-amber-900/50';
    case 'D':
      return 'text-orange-300 bg-orange-900/50';
    default:
      return 'text-red-300 bg-red-900/50';
  }
}

function severityColor(s: string) {
  switch (s) {
    case 'critical':
      return 'bg-red-900/60 text-red-300';
    case 'high':
      return 'bg-orange-900/60 text-orange-300';
    case 'medium':
      return 'bg-amber-900/60 text-amber-300';
    case 'low':
      return 'bg-sky-900/60 text-sky-300';
    default:
      return 'bg-zinc-700 text-zinc-300';
  }
}

function agentStatusColor(s: string) {
  switch (s) {
    case 'healthy':
      return 'bg-emerald-900/60 text-emerald-300';
    case 'degraded':
      return 'bg-amber-900/60 text-amber-300';
    case 'offline':
    case 'not_installed':
      return 'bg-red-900/60 text-red-300';
    default:
      return 'bg-zinc-700 text-zinc-300';
  }
}

function matrixStatusBadge(status: string) {
  const map: Record<string, string> = {
    protected: 'bg-emerald-900/60 text-emerald-300 border-emerald-700/40',
    at_risk: 'bg-amber-900/60 text-amber-300 border-amber-700/40',
    outdated: 'bg-orange-900/60 text-orange-300 border-orange-700/40',
    not_installed: 'bg-red-900/50 text-red-300 border-red-700/40',
    offline: 'bg-zinc-700 text-zinc-300 border-zinc-600',
    unknown: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  };
  const cls = map[status] || map.unknown;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function boolBadge(v: boolean | null | undefined, yes = 'On', no = 'Off') {
  if (v === true)
    return <span className="text-xs text-emerald-300">{yes}</span>;
  if (v === false)
    return <span className="text-xs text-red-300">{no}</span>;
  return <span className="text-xs text-zinc-500">—</span>;
}

export default function EndpointSecurityPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>('matrix');
  const [providers, setProviders] = useState<SecurityProvider[]>([]);
  const [agents, setAgents] = useState<EndpointSecurityAgent[]>([]);
  const [findings, setFindings] = useState<SecurityFinding[]>([]);
  const [scores, setScores] = useState<EndpointSecurityScore[]>([]);
  const [org, setOrg] = useState<OrgSecurityScore | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [matrix, setMatrix] = useState<SecurityMatrixResponse | null>(null);
  const [connectors, setConnectors] = useState<string[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Matrix filters
  const [matrixHostname, setMatrixHostname] = useState('');
  const [matrixProduct, setMatrixProduct] = useState('');
  const [matrixStatus, setMatrixStatus] = useState('');
  const [matrixInstalledOnly, setMatrixInstalledOnly] = useState(false);

  const [findingFilter, setFindingFilter] = useState({ status: 'open', severity: '' });
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [showFindingForm, setShowFindingForm] = useState(false);
  const [configProvider, setConfigProvider] = useState<SecurityProvider | null>(null);
  const [configJson, setConfigJson] = useState('{}');

  const [agentForm, setAgentForm] = useState({
    provider_id: '',
    device_id: '',
    hostname: '',
    status: 'healthy',
    real_time_protection: true,
    definitions_up_to_date: true,
    agent_version: '',
  });

  const [findingForm, setFindingForm] = useState({
    provider_id: '',
    device_id: '',
    hostname: '',
    title: '',
    severity: 'medium',
    status: 'open',
    category: 'malware',
    description: '',
  });

  const flash = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 3000);
  };

  const loadData = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [p, a, f, s, o, d, m, c] = await Promise.all([
        listSecurityProviders(),
        listSecurityAgents(),
        listSecurityFindings({
          status: findingFilter.status || undefined,
          severity: findingFilter.severity || undefined,
        }),
        listSecurityScores(),
        getOrgSecurityScore().catch(() => null),
        getDevices().catch(() => [] as Device[]),
        getSecurityMatrix().catch(() => null),
        listSecurityConnectors().catch(() => ({ connectors: [] as string[] })),
      ]);
      setProviders(p);
      setAgents(a);
      setFindings(f);
      setScores(s);
      setOrg(o);
      setDevices(d);
      setMatrix(m);
      setConnectors(c.connectors || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load endpoint security data');
    } finally {
      setBusy(false);
    }
  }, [findingFilter.status, findingFilter.severity]);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [loading, user, router]);

  useEffect(() => {
    if (!loading && user) loadData();
  }, [loading, user, loadData]);

  const enabledProviders = useMemo(
    () => providers.filter((p) => p.enabled),
    [providers]
  );

  const filteredMatrixRows = useMemo(() => {
    if (!matrix?.rows) return [];
    return matrix.rows.filter((r) => {
      if (matrixHostname && !(r.hostname || '').toLowerCase().includes(matrixHostname.toLowerCase()))
        return false;
      if (matrixProduct && r.provider_key !== matrixProduct) return false;
      if (matrixStatus && r.status !== matrixStatus) return false;
      if (matrixInstalledOnly && !r.installed) return false;
      return true;
    });
  }, [matrix, matrixHostname, matrixProduct, matrixStatus, matrixInstalledOnly]);

  const matrixSummary = useMemo(() => {
    const rows = filteredMatrixRows;
    return {
      total: rows.length,
      protected: rows.filter((r) => r.status === 'protected').length,
      atRisk: rows.filter((r) => r.status === 'at_risk').length,
      outdated: rows.filter((r) => r.status === 'outdated').length,
      notInstalled: rows.filter((r) => r.status === 'not_installed').length,
      withThreats: rows.filter((r) => (r.threats_found || 0) > 0).length,
    };
  }, [filteredMatrixRows]);

  const seedProviders = async () => {
    try {
      setBusy(true);
      const created = await seedSecurityProviders();
      flash(
        created.length
          ? `Seeded ${created.length} providers`
          : 'Catalog already present (idempotent)'
      );
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to seed providers');
    } finally {
      setBusy(false);
    }
  };

  const toggleProvider = async (p: SecurityProvider) => {
    try {
      await updateSecurityProvider(p.id, { enabled: !p.enabled });
      flash(`${p.display_name} ${!p.enabled ? 'enabled' : 'disabled'}`);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to update provider');
    }
  };

  const openConfig = (p: SecurityProvider) => {
    setConfigProvider(p);
    setConfigJson(JSON.stringify(p.config || {}, null, 2));
  };

  const saveConfig = async () => {
    if (!configProvider) return;
    try {
      setBusy(true);
      let parsed: Record<string, any> = {};
      try {
        parsed = JSON.parse(configJson || '{}');
      } catch {
        setError('Config must be valid JSON');
        return;
      }
      await updateSecurityProvider(configProvider.id, { config: parsed });
      flash(`Saved cloud config for ${configProvider.display_name}`);
      setConfigProvider(null);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to save config');
    } finally {
      setBusy(false);
    }
  };

  const runSync = async (p: SecurityProvider) => {
    try {
      setBusy(true);
      const res = await syncSecurityProvider(p.id);
      flash(
        `${p.display_name}: ${res.status} · agents ${res.agents_upserted}` +
          (res.errors?.length ? ` · ${res.errors[0]}` : '')
      );
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Cloud sync failed');
    } finally {
      setBusy(false);
    }
  };

  const runSyncAll = async () => {
    try {
      setBusy(true);
      const res = await syncAllSecurityProviders();
      const n = res.results?.length || 0;
      flash(`Cloud sync finished for ${n} provider(s)`);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Sync-all failed');
    } finally {
      setBusy(false);
    }
  };

  const saveAgent = async () => {
    try {
      setBusy(true);
      setError(null);
      await createSecurityAgent({
        provider_id: agentForm.provider_id,
        device_id: agentForm.device_id || null,
        hostname: agentForm.hostname || null,
        status: agentForm.status,
        real_time_protection: agentForm.real_time_protection,
        definitions_up_to_date: agentForm.definitions_up_to_date,
        agent_version: agentForm.agent_version || null,
      });
      flash('Agent registered');
      setShowAgentForm(false);
      setAgentForm({
        provider_id: '',
        device_id: '',
        hostname: '',
        status: 'healthy',
        real_time_protection: true,
        definitions_up_to_date: true,
        agent_version: '',
      });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to create agent');
    } finally {
      setBusy(false);
    }
  };

  const saveFinding = async () => {
    try {
      setBusy(true);
      setError(null);
      await createSecurityFinding({
        provider_id: findingForm.provider_id,
        device_id: findingForm.device_id || null,
        hostname: findingForm.hostname || null,
        title: findingForm.title,
        severity: findingForm.severity,
        status: findingForm.status,
        category: findingForm.category || null,
        description: findingForm.description || null,
      });
      flash('Finding recorded');
      setShowFindingForm(false);
      setFindingForm({
        provider_id: '',
        device_id: '',
        hostname: '',
        title: '',
        severity: 'medium',
        status: 'open',
        category: 'malware',
        description: '',
      });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to create finding');
    } finally {
      setBusy(false);
    }
  };

  const resolveFinding = async (f: SecurityFinding, status: string) => {
    try {
      await updateSecurityFinding(f.id, { status });
      flash(`Finding marked ${status}`);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to update finding');
    }
  };

  const recompute = async () => {
    try {
      setBusy(true);
      const res = await recomputeAllSecurityScores();
      flash(`Recomputed ${res.devices_scored} device scores`);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to recompute scores');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <ModuleShell title="Endpoint Security">
        <div className="text-slate-500">Loading…</div>
      </ModuleShell>
    );
  }

  return (
    <ModuleShell title="Endpoint Security" subtitle="Fleet matrix · providers · cloud sync · scores">
      <div className="space-y-6">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/dashboard')}
              className="p-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                <Shield className="text-emerald-400" /> Endpoint Security
              </h1>
              <p className="text-zinc-400 text-sm mt-1">
                Windows Defender · CrowdStrike · SentinelOne · Huntress · Sophos · Bitdefender · ThreatLocker
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={loadData}
              className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 px-4 py-2.5 rounded-xl text-sm"
            >
              <RefreshCw size={16} className={busy ? 'animate-spin' : ''} /> Refresh
            </button>
            <button
              onClick={runSyncAll}
              className="flex items-center gap-2 bg-sky-800 hover:bg-sky-700 px-4 py-2.5 rounded-xl text-sm"
            >
              <Cloud size={16} /> Sync all cloud
            </button>
            <button
              onClick={recompute}
              className="flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 px-4 py-2.5 rounded-xl text-sm font-medium"
            >
              <Activity size={16} /> Recompute Scores
            </button>
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

        {org && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-4">
              <div className="text-xs text-zinc-400 mb-1">Avg score</div>
              <div className="text-2xl font-bold text-emerald-300">{org.average_score}</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-4">
              <div className="text-xs text-zinc-400 mb-1">Median</div>
              <div className="text-2xl font-bold">{org.median_score}</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-4">
              <div className="text-xs text-zinc-400 mb-1">Devices scored</div>
              <div className="text-2xl font-bold">{org.devices_scored}</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-4">
              <div className="text-xs text-zinc-400 mb-1">Open critical</div>
              <div className="text-2xl font-bold text-red-400">{org.open_critical_total}</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-4">
              <div className="text-xs text-zinc-400 mb-1">Open high</div>
              <div className="text-2xl font-bold text-orange-400">{org.open_high_total}</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-4">
              <div className="text-xs text-zinc-400 mb-1">Agents healthy</div>
              <div className="text-2xl font-bold">
                {org.agents_healthy}/{org.agents_total}
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-4">
          {(
            [
              ['matrix', 'Matrix'],
              ['overview', 'Overview'],
              ['providers', `Providers (${providers.length})`],
              ['agents', `Agents (${agents.length})`],
              ['findings', `Findings (${findings.length})`],
              ['scores', `Scores (${scores.length})`],
            ] as [Tab, string][]
          ).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition ${
                tab === id
                  ? 'bg-emerald-600 text-white'
                  : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ========== MATRIX ========== */}
        {tab === 'matrix' && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-3 items-end bg-zinc-900 border border-zinc-700 rounded-2xl p-4">
              <div className="flex items-center gap-2 text-zinc-400 text-sm">
                <Filter size={16} /> Filters
              </div>
              <div>
                <label className="text-xs text-zinc-500">Hostname</label>
                <input
                  className="block mt-1 bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm w-44"
                  placeholder="Search host…"
                  value={matrixHostname}
                  onChange={(e) => setMatrixHostname(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-zinc-500">Product</label>
                <select
                  className="block mt-1 bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm"
                  value={matrixProduct}
                  onChange={(e) => setMatrixProduct(e.target.value)}
                >
                  <option value="">All products</option>
                  {(matrix?.products || providers).map((p: any) => (
                    <option key={p.provider_key || p.id} value={p.provider_key}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-500">Status</label>
                <select
                  className="block mt-1 bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm"
                  value={matrixStatus}
                  onChange={(e) => setMatrixStatus(e.target.value)}
                >
                  <option value="">All</option>
                  <option value="protected">protected</option>
                  <option value="at_risk">at_risk</option>
                  <option value="outdated">outdated</option>
                  <option value="not_installed">not_installed</option>
                  <option value="offline">offline</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={matrixInstalledOnly}
                  onChange={(e) => setMatrixInstalledOnly(e.target.checked)}
                  className="rounded"
                />
                Installed only
              </label>
              <div className="ml-auto flex flex-wrap gap-2 text-xs">
                <span className="px-2 py-1 rounded-lg bg-zinc-800 text-zinc-300">{matrixSummary.total} rows</span>
                <span className="px-2 py-1 rounded-lg bg-emerald-900/40 text-emerald-300">{matrixSummary.protected} protected</span>
                <span className="px-2 py-1 rounded-lg bg-amber-900/40 text-amber-300">{matrixSummary.atRisk} at risk</span>
                <span className="px-2 py-1 rounded-lg bg-orange-900/40 text-orange-300">{matrixSummary.outdated} outdated</span>
                <span className="px-2 py-1 rounded-lg bg-red-900/40 text-red-300">{matrixSummary.notInstalled} missing</span>
                {matrixSummary.withThreats > 0 && (
                  <span className="px-2 py-1 rounded-lg bg-red-900/60 text-red-200">{matrixSummary.withThreats} with threats</span>
                )}
              </div>
            </div>

            <div className="bg-zinc-900 border border-zinc-700 rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-700 text-left text-xs text-zinc-400 uppercase tracking-wide">
                      <th className="px-4 py-3 font-medium">Hostname</th>
                      <th className="px-4 py-3 font-medium">Product</th>
                      <th className="px-4 py-3 font-medium">Installed</th>
                      <th className="px-4 py-3 font-medium">Version</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">RTP</th>
                      <th className="px-4 py-3 font-medium">Defs</th>
                      <th className="px-4 py-3 font-medium">Last scan</th>
                      <th className="px-4 py-3 font-medium">Threats</th>
                      <th className="px-4 py-3 font-medium">Last seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMatrixRows.length === 0 && (
                      <tr>
                        <td colSpan={10} className="px-4 py-12 text-center text-zinc-500">
                          {matrix ? (
                            <>
                              No rows match filters. Deploy agents or run{' '}
                              <button onClick={seedProviders} className="text-emerald-400 underline">
                                seed providers
                              </button>{' '}
                              then wait for agent reports / cloud sync.
                            </>
                          ) : (
                            'Loading matrix…'
                          )}
                        </td>
                      </tr>
                    )}
                    {filteredMatrixRows.map((r, i) => (
                      <tr
                        key={`${r.hostname}-${r.provider_key}-${i}`}
                        className="border-b border-zinc-800/80 hover:bg-zinc-800/40"
                      >
                        <td className="px-4 py-3 font-medium text-zinc-100">
                          {r.hostname || r.device_id?.slice(0, 8) || '—'}
                        </td>
                        <td className="px-4 py-3 text-zinc-300">{r.product_name || r.provider_key}</td>
                        <td className="px-4 py-3">{r.installed ? (
                          <span className="text-emerald-300">Yes</span>
                        ) : (
                          <span className="text-red-300">No</span>
                        )}</td>
                        <td className="px-4 py-3 text-zinc-400 font-mono text-xs">{r.version || '—'}</td>
                        <td className="px-4 py-3">{matrixStatusBadge(r.status)}</td>
                        <td className="px-4 py-3">{boolBadge(r.real_time_protection)}</td>
                        <td className="px-4 py-3">{boolBadge(r.definitions_up_to_date, 'Current', 'Stale')}</td>
                        <td className="px-4 py-3 text-zinc-400 text-xs">
                          {r.last_scan_at ? new Date(r.last_scan_at).toLocaleString() : '—'}
                        </td>
                        <td className="px-4 py-3">
                          {(r.threats_found || 0) > 0 ? (
                            <span className="text-red-300 font-medium">
                              {r.threats_found}
                              {(r.threats_critical || 0) > 0 && (
                                <span className="text-xs ml-1 text-red-400">
                                  ({r.threats_critical} crit)
                                </span>
                              )}
                            </span>
                          ) : (
                            <span className="text-zinc-500">0</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-zinc-400 text-xs">
                          {r.last_seen_at ? new Date(r.last_seen_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {matrix?.generated_at && (
                <div className="px-4 py-2 border-t border-zinc-800 text-xs text-zinc-500 flex items-center gap-2">
                  <Table2 size={12} />
                  Generated {new Date(matrix.generated_at).toLocaleString()} · {matrix.total_rows} total rows
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========== OVERVIEW ========== */}
        {tab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Server size={18} className="text-emerald-400" /> Grade distribution
              </h3>
              {org ? (
                <div className="flex flex-wrap gap-3">
                  {Object.entries(org.grade_distribution).map(([g, n]) => (
                    <div
                      key={g}
                      className={`px-4 py-3 rounded-2xl text-center min-w-[64px] ${gradeColor(g)}`}
                    >
                      <div className="text-xl font-bold">{g}</div>
                      <div className="text-xs opacity-80">{n}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-zinc-500 text-sm">No scores yet. Register agents and recompute.</p>
              )}
            </div>
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle size={18} className="text-amber-400" /> Recent open findings
              </h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {findings.filter((f) => f.status === 'open' || f.status === 'investigating').slice(0, 8)
                  .length === 0 && (
                  <p className="text-zinc-500 text-sm">No open findings</p>
                )}
                {findings
                  .filter((f) => f.status === 'open' || f.status === 'investigating')
                  .slice(0, 8)
                  .map((f) => (
                    <div
                      key={f.id}
                      className="text-sm bg-zinc-800/50 border border-zinc-700 rounded-xl px-3 py-2 flex justify-between gap-2"
                    >
                      <span className="truncate">{f.title}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${severityColor(f.severity)}`}>
                        {f.severity}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
            <div className="lg:col-span-2 bg-zinc-900 border border-zinc-700 rounded-3xl p-6">
              <h3 className="font-semibold mb-4">Enabled products</h3>
              <div className="flex flex-wrap gap-2">
                {enabledProviders.length === 0 && (
                  <p className="text-zinc-500 text-sm">
                    No providers enabled.{' '}
                    <button onClick={() => setTab('providers')} className="text-emerald-400 underline">
                      Configure providers
                    </button>
                  </p>
                )}
                {enabledProviders.map((p) => (
                  <span
                    key={p.id}
                    className="px-3 py-1.5 rounded-full bg-emerald-900/40 text-emerald-300 text-sm border border-emerald-700/40"
                  >
                    {p.display_name}
                    {p.last_sync_status && (
                      <span className="text-zinc-400 ml-2 text-xs">{p.last_sync_status}</span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ========== PROVIDERS ========== */}
        {tab === 'providers' && (
          <div className="space-y-4">
            <div className="flex flex-wrap justify-between gap-2">
              <p className="text-sm text-zinc-400">
                Seed once per tenant. Cloud connectors: {(connectors.length ? connectors : [...CLOUD_CONNECTOR_KEYS]).join(', ')}.
                Agent-side detection works for all catalog products.
              </p>
              <button
                onClick={seedProviders}
                className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 px-4 py-2.5 rounded-xl text-sm"
              >
                Seed catalog (9 products)
              </button>
            </div>
            {providers.length === 0 && !busy && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                No providers configured. Click &quot;Seed catalog&quot; to add Windows Defender, CrowdStrike,
                SentinelOne, and more.
              </div>
            )}
            {providers.map((p) => {
              const hasCloud = CLOUD_CONNECTOR_KEYS.has(p.provider_key) || connectors.includes(p.provider_key);
              return (
                <div
                  key={p.id}
                  className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col gap-4"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-3 mb-1">
                        <h3 className="text-lg font-semibold">{p.display_name}</h3>
                        <span className="text-xs text-zinc-400">{p.provider_key}</span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            p.enabled
                              ? 'bg-emerald-900/60 text-emerald-300'
                              : 'bg-zinc-700 text-zinc-400'
                          }`}
                        >
                          {p.enabled ? 'enabled' : 'disabled'}
                        </span>
                        {hasCloud && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-sky-900/50 text-sky-300 border border-sky-700/40">
                            cloud API
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-zinc-400">
                        Sync: {p.last_sync_status || 'never'}
                        {p.last_sync_at && ` · ${new Date(p.last_sync_at).toLocaleString()}`}
                        {p.last_sync_error && (
                          <span className="text-red-400"> · {p.last_sync_error}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {hasCloud && (
                        <>
                          <button
                            onClick={() => openConfig(p)}
                            className="px-3 py-2 rounded-xl text-sm bg-zinc-800 hover:bg-zinc-700"
                          >
                            Cloud config
                          </button>
                          <button
                            onClick={() => runSync(p)}
                            disabled={!p.enabled}
                            className="px-3 py-2 rounded-xl text-sm bg-sky-800 hover:bg-sky-700 disabled:opacity-40"
                          >
                            Sync now
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => toggleProvider(p)}
                        className={`px-4 py-2 rounded-xl text-sm font-medium ${
                          p.enabled
                            ? 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
                            : 'bg-emerald-700 hover:bg-emerald-600'
                        }`}
                      >
                        {p.enabled ? 'Disable' : 'Enable'}
                      </button>
                    </div>
                  </div>
                  {hasCloud && (
                    <p className="text-xs text-zinc-500">
                      Config keys: {(CONFIG_HINTS[p.provider_key] || ['see docs']).join(', ')}. Stored in
                      provider.config (never logged).
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ========== AGENTS ========== */}
        {tab === 'agents' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <button
                onClick={() => setShowAgentForm(true)}
                className="flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 px-4 py-2.5 rounded-xl text-sm"
              >
                <Plus size={16} /> Register agent
              </button>
            </div>
            {agents.length === 0 && !busy && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                No agents yet. Deploy the Bhudi agent (endpoint security scan runs periodically) or use
                cloud sync.
              </div>
            )}
            {agents.map((a) => (
              <div
                key={a.id}
                className="bg-zinc-900 border border-zinc-700 rounded-3xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-semibold">{a.hostname || a.device_id?.slice(0, 8) || 'Unknown'}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${agentStatusColor(a.status)}`}>
                      {a.status}
                    </span>
                    <span className="text-xs text-zinc-400">{a.provider_name || a.provider_key}</span>
                  </div>
                  <div className="text-xs text-zinc-500 flex flex-wrap gap-3">
                    {a.agent_version && <span>v{a.agent_version}</span>}
                    <span>RTP {a.real_time_protection == null ? '—' : a.real_time_protection ? 'on' : 'off'}</span>
                    {a.last_seen_at && <span>seen {new Date(a.last_seen_at).toLocaleString()}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ========== FINDINGS ========== */}
        {tab === 'findings' && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-3 items-end justify-between">
              <div className="flex gap-2">
                <select
                  className="bg-zinc-800 border border-zinc-600 rounded-xl px-3 py-2 text-sm"
                  value={findingFilter.status}
                  onChange={(e) => setFindingFilter({ ...findingFilter, status: e.target.value })}
                >
                  <option value="">All statuses</option>
                  <option value="open">open</option>
                  <option value="investigating">investigating</option>
                  <option value="contained">contained</option>
                  <option value="resolved">resolved</option>
                  <option value="false_positive">false_positive</option>
                </select>
                <select
                  className="bg-zinc-800 border border-zinc-600 rounded-xl px-3 py-2 text-sm"
                  value={findingFilter.severity}
                  onChange={(e) => setFindingFilter({ ...findingFilter, severity: e.target.value })}
                >
                  <option value="">All severities</option>
                  <option value="critical">critical</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                </select>
              </div>
              <button
                onClick={() => setShowFindingForm(true)}
                className="flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 px-4 py-2.5 rounded-xl text-sm"
              >
                <Plus size={16} /> Add finding
              </button>
            </div>
            {findings.length === 0 && !busy && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                No findings match the current filters.
              </div>
            )}
            {findings.map((f) => (
              <div
                key={f.id}
                className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-3 mb-1">
                    <h3 className="font-semibold">{f.title}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${severityColor(f.severity)}`}>
                      {f.severity}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-700 text-zinc-300">
                      {f.status}
                    </span>
                  </div>
                  <div className="text-xs text-zinc-400 flex flex-wrap gap-3">
                    <span>{f.provider_key || f.provider_id.slice(0, 8)}</span>
                    {(f.hostname || f.device_id) && (
                      <span>{f.hostname || f.device_id?.slice(0, 8)}</span>
                    )}
                    {f.category && <span>{f.category}</span>}
                    {f.detected_at && (
                      <span>{new Date(f.detected_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>
                {['open', 'investigating', 'contained'].includes(f.status) && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => resolveFinding(f, 'resolved')}
                      className="flex items-center gap-1 px-3 py-2 rounded-xl bg-emerald-900/40 text-emerald-300 text-xs hover:bg-emerald-800/50"
                    >
                      <CheckCircle2 size={14} /> Resolve
                    </button>
                    <button
                      onClick={() => resolveFinding(f, 'false_positive')}
                      className="px-3 py-2 rounded-xl bg-zinc-800 text-zinc-300 text-xs hover:bg-zinc-700"
                    >
                      False positive
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ========== SCORES ========== */}
        {tab === 'scores' && (
          <div className="space-y-4">
            {scores.length === 0 && !busy && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                No device scores yet. Agents report → recompute scores.
              </div>
            )}
            {scores.map((s) => (
              <div
                key={s.id}
                className="bg-zinc-900 border border-zinc-700 rounded-3xl p-5 flex items-center justify-between gap-4"
              >
                <div>
                  <div className="font-semibold">{s.hostname || s.device_id.slice(0, 8)}</div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {s.agents_healthy}/{s.agents_total} healthy · {s.open_critical} crit · {s.open_high} high
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-2xl font-bold px-3 py-1 rounded-xl ${gradeColor(s.grade)}`}>
                    {s.grade}
                  </span>
                  <span className="text-xl font-mono text-zinc-200">{s.score}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Agent form modal */}
        {showAgentForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 w-full max-w-lg">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold">Register security agent</h3>
                <button onClick={() => setShowAgentForm(false)}>
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-400">Provider</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.provider_id}
                    onChange={(e) => setAgentForm({ ...agentForm, provider_id: e.target.value })}
                  >
                    <option value="">Select…</option>
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Hostname</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.hostname}
                    onChange={(e) => setAgentForm({ ...agentForm, hostname: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Device ID (optional)</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.device_id}
                    onChange={(e) => setAgentForm({ ...agentForm, device_id: e.target.value })}
                  >
                    <option value="">None</option>
                    {devices.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.hostname || d.name || d.id.slice(0, 8)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-400">Status</label>
                    <select
                      className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                      value={agentForm.status}
                      onChange={(e) => setAgentForm({ ...agentForm, status: e.target.value })}
                    >
                      <option value="healthy">healthy</option>
                      <option value="degraded">degraded</option>
                      <option value="offline">offline</option>
                      <option value="not_installed">not_installed</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400">Version</label>
                    <input
                      className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                      value={agentForm.agent_version}
                      onChange={(e) => setAgentForm({ ...agentForm, agent_version: e.target.value })}
                    />
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button onClick={() => setShowAgentForm(false)} className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm">
                  Cancel
                </button>
                <button
                  onClick={saveAgent}
                  disabled={!agentForm.provider_id || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Save
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Finding form modal */}
        {showFindingForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold">Record finding</h3>
                <button onClick={() => setShowFindingForm(false)}>
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-400">Provider</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={findingForm.provider_id}
                    onChange={(e) => setFindingForm({ ...findingForm, provider_id: e.target.value })}
                  >
                    <option value="">Select…</option>
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Title</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={findingForm.title}
                    onChange={(e) => setFindingForm({ ...findingForm, title: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-400">Severity</label>
                    <select
                      className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                      value={findingForm.severity}
                      onChange={(e) => setFindingForm({ ...findingForm, severity: e.target.value })}
                    >
                      <option value="critical">critical</option>
                      <option value="high">high</option>
                      <option value="medium">medium</option>
                      <option value="low">low</option>
                      <option value="info">info</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400">Category</label>
                    <input
                      className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                      value={findingForm.category}
                      onChange={(e) => setFindingForm({ ...findingForm, category: e.target.value })}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Hostname</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={findingForm.hostname}
                    onChange={(e) => setFindingForm({ ...findingForm, hostname: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Description</label>
                  <textarea
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm min-h-[80px]"
                    value={findingForm.description}
                    onChange={(e) => setFindingForm({ ...findingForm, description: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button onClick={() => setShowFindingForm(false)} className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm">
                  Cancel
                </button>
                <button
                  onClick={saveFinding}
                  disabled={!findingForm.provider_id || !findingForm.title || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Save
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Cloud config modal */}
        {configProvider && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 w-full max-w-lg">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">
                  Cloud config · {configProvider.display_name}
                </h3>
                <button onClick={() => setConfigProvider(null)}>
                  <X size={20} />
                </button>
              </div>
              <p className="text-xs text-zinc-500 mb-3">
                Keys: {(CONFIG_HINTS[configProvider.provider_key] || []).join(', ') || 'JSON object'}.
                Secrets stay server-side.
              </p>
              <textarea
                className="w-full bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-3 text-sm font-mono min-h-[180px]"
                value={configJson}
                onChange={(e) => setConfigJson(e.target.value)}
                spellCheck={false}
              />
              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => setConfigProvider(null)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={saveConfig}
                  disabled={busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Save config
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ModuleShell>
  );
}
