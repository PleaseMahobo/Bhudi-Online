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
  getDevices,
  type SecurityProvider,
  type EndpointSecurityAgent,
  type SecurityFinding,
  type EndpointSecurityScore,
  type OrgSecurityScore,
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
} from 'lucide-react';

type Tab = 'overview' | 'providers' | 'agents' | 'findings' | 'scores';

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

export default function EndpointSecurityPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>('overview');
  const [providers, setProviders] = useState<SecurityProvider[]>([]);
  const [agents, setAgents] = useState<EndpointSecurityAgent[]>([]);
  const [findings, setFindings] = useState<SecurityFinding[]>([]);
  const [scores, setScores] = useState<EndpointSecurityScore[]>([]);
  const [org, setOrg] = useState<OrgSecurityScore | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [findingFilter, setFindingFilter] = useState({ status: 'open', severity: '' });
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [showFindingForm, setShowFindingForm] = useState(false);

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
    setTimeout(() => setSuccess(null), 2500);
  };

  const loadData = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [p, a, f, s, o, d] = await Promise.all([
        listSecurityProviders(),
        listSecurityAgents(),
        listSecurityFindings({
          status: findingFilter.status || undefined,
          severity: findingFilter.severity || undefined,
        }),
        listSecurityScores(),
        getOrgSecurityScore().catch(() => null),
        getDevices().catch(() => [] as Device[]),
      ]);
      setProviders(p);
      setAgents(a);
      setFindings(f);
      setScores(s);
      setOrg(o);
      setDevices(d);
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

  const seedProviders = async () => {
    try {
      setBusy(true);
      await seedSecurityProviders();
      flash('Provider catalog seeded');
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
    <ModuleShell title="Endpoint Security" subtitle="Providers, agents, findings & security scores">
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
                <Shield className="text-emerald-400" /> Endpoint Security
              </h1>
              <p className="text-zinc-400 text-sm mt-1">
                Defender · CrowdStrike · SentinelOne · Huntress · Sophos · Security score
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
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
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

        <div className="flex flex-wrap gap-2 mb-6">
          {(
            [
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

        {tab === 'providers' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <button
                onClick={seedProviders}
                className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 px-4 py-2.5 rounded-xl text-sm"
              >
                Seed catalog (9 products)
              </button>
            </div>
            {providers.length === 0 && !busy && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                No providers configured. Click "Seed catalog" to add Windows Defender, CrowdStrike,
                SentinelOne, and more.
              </div>
            )}
            {providers.map((p) => (
              <div
                key={p.id}
                className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
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
                  </div>
                  <div className="text-xs text-zinc-400">
                    Sync: {p.last_sync_status || 'never'}
                    {p.last_sync_at && ` · ${new Date(p.last_sync_at).toLocaleString()}`}
                    {p.last_sync_error && (
                      <span className="text-red-400"> · {p.last_sync_error}</span>
                    )}
                  </div>
                </div>
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
            ))}
          </div>
        )}

        {tab === 'agents' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <button
                onClick={() => setShowAgentForm(true)}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 rounded-xl text-sm font-medium"
              >
                <Plus size={18} /> Register Agent
              </button>
            </div>
            {agents.length === 0 && !busy && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                No security agents registered yet.
              </div>
            )}
            {agents.map((a) => (
              <div
                key={a.id}
                className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-3 mb-1">
                    <h3 className="font-semibold">
                      {a.hostname || a.device_id?.slice(0, 8) || a.id.slice(0, 8)}
                    </h3>
                    <span className="text-xs text-zinc-400">
                      {a.provider_name || a.provider_key || a.provider_id.slice(0, 8)}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${agentStatusColor(a.status)}`}>
                      {a.status}
                    </span>
                  </div>
                  <div className="text-xs text-zinc-400 flex flex-wrap gap-3">
                    {a.agent_version && <span>v{a.agent_version}</span>}
                    <span>RTP: {a.real_time_protection ? 'on' : a.real_time_protection === false ? 'off' : '?'}</span>
                    <span>
                      Defs:{' '}
                      {a.definitions_up_to_date
                        ? 'current'
                        : a.definitions_up_to_date === false
                          ? 'stale'
                          : '?'}
                    </span>
                    {a.last_seen_at && (
                      <span>seen {new Date(a.last_seen_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'findings' && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-3 items-center justify-between">
              <div className="flex gap-2">
                <select
                  className="bg-zinc-800 border border-zinc-600 rounded-xl px-3 py-2 text-sm"
                  value={findingFilter.status}
                  onChange={(e) =>
                    setFindingFilter({ ...findingFilter, status: e.target.value })
                  }
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
                  onChange={(e) =>
                    setFindingFilter({ ...findingFilter, severity: e.target.value })
                  }
                >
                  <option value="">All severities</option>
                  <option value="critical">critical</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="info">info</option>
                </select>
              </div>
              <button
                onClick={() => setShowFindingForm(true)}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 rounded-xl text-sm font-medium"
              >
                <Plus size={18} /> Add Finding
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

        {tab === 'scores' && (
          <div className="space-y-4">
            {scores.length === 0 && !busy && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                No device security scores yet. Register agents, then click Recompute Scores.
              </div>
            )}
            {scores
              .slice()
              .sort((a, b) => a.score - b.score)
              .map((s) => (
                <div
                  key={s.id}
                  className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div>
                    <div className="flex flex-wrap items-center gap-3 mb-1">
                      <h3 className="font-semibold">
                        {s.hostname || s.device_id.slice(0, 8)}
                      </h3>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-bold ${gradeColor(s.grade)}`}
                      >
                        {s.grade}
                      </span>
                    </div>
                    <div className="text-xs text-zinc-400">
                      Agents {s.agents_healthy}/{s.agents_total} · Critical {s.open_critical} · High{' '}
                      {s.open_high}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-emerald-300">{s.score}</div>
                    <div className="text-xs text-zinc-500">
                      {new Date(s.computed_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}

        {showAgentForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">Register Security Agent</h2>
                <button
                  onClick={() => setShowAgentForm(false)}
                  className="p-2 hover:bg-zinc-800 rounded-xl"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-400">Provider *</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.provider_id}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, provider_id: e.target.value })
                    }
                  >
                    <option value="">Select provider…</option>
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Device</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.device_id}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, device_id: e.target.value })
                    }
                  >
                    <option value="">Optional device…</option>
                    {devices.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.hostname || d.name || d.id}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Hostname</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.hostname}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, hostname: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Status</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.status}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, status: e.target.value })
                    }
                  >
                    <option value="healthy">healthy</option>
                    <option value="degraded">degraded</option>
                    <option value="offline">offline</option>
                    <option value="not_installed">not_installed</option>
                    <option value="unknown">unknown</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Agent version</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={agentForm.agent_version}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, agent_version: e.target.value })
                    }
                  />
                </div>
                <div className="flex gap-4 text-sm">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={agentForm.real_time_protection}
                      onChange={(e) =>
                        setAgentForm({
                          ...agentForm,
                          real_time_protection: e.target.checked,
                        })
                      }
                    />
                    Real-time protection
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={agentForm.definitions_up_to_date}
                      onChange={(e) =>
                        setAgentForm({
                          ...agentForm,
                          definitions_up_to_date: e.target.checked,
                        })
                      }
                    />
                    Definitions current
                  </label>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowAgentForm(false)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
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

        {showFindingForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">Add Security Finding</h2>
                <button
                  onClick={() => setShowFindingForm(false)}
                  className="p-2 hover:bg-zinc-800 rounded-xl"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-400">Provider *</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={findingForm.provider_id}
                    onChange={(e) =>
                      setFindingForm({ ...findingForm, provider_id: e.target.value })
                    }
                  >
                    <option value="">Select provider…</option>
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Title *</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={findingForm.title}
                    onChange={(e) =>
                      setFindingForm({ ...findingForm, title: e.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-400">Severity</label>
                    <select
                      className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                      value={findingForm.severity}
                      onChange={(e) =>
                        setFindingForm({ ...findingForm, severity: e.target.value })
                      }
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
                      onChange={(e) =>
                        setFindingForm({ ...findingForm, category: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Hostname</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={findingForm.hostname}
                    onChange={(e) =>
                      setFindingForm({ ...findingForm, hostname: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Description</label>
                  <textarea
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm min-h-[80px]"
                    value={findingForm.description}
                    onChange={(e) =>
                      setFindingForm({ ...findingForm, description: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowFindingForm(false)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
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
      </div>
    </ModuleShell>
  );
}
