'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { useRouter } from 'next/navigation';
import {
  listPackages,
  createPackage,
  deletePackage,
  listDeploymentJobs,
  createDeploymentJob,
  startDeploymentJob,
  cancelDeploymentJob,
  rollbackDeploymentJob,
  getDeploymentSummary,
  listDeploymentEvents,
  getDevices,
  type SoftwarePackage,
  type DeploymentJob,
  type DeploymentJobSummary,
  type DeploymentEvent,
  type Device,
} from '@/lib/api';
import {
  Download,
  Plus,
  Trash2,
  ArrowLeft,
  Save,
  X,
  RefreshCw,
  Play,
  Square,
  RotateCcw,
  Package,
} from 'lucide-react';

type Tab = 'packages' | 'jobs';

const PACKAGE_TYPES = ['msi', 'exe', 'chocolatey', 'winget', 'custom'] as const;

const emptyPkg = {
  name: '',
  version: '1.0.0',
  publisher: '',
  description: '',
  package_type: 'msi',
  source_url: '',
  file_name: '',
  sha256: '',
  choco_id: '',
  winget_id: '',
  install_args: '',
  uninstall_args: '',
  uninstall_command: '',
  requires_reboot: false,
  requires_elevation: true,
  timeout_seconds: 3600,
  architecture: 'any',
};

function statusColor(s: string) {
  switch (s) {
    case 'completed':
    case 'success':
      return 'bg-emerald-900/60 text-emerald-300';
    case 'failed':
      return 'bg-red-900/60 text-red-300';
    case 'running':
    case 'installing':
    case 'downloading':
      return 'bg-sky-900/60 text-sky-300';
    case 'queued':
    case 'pending':
      return 'bg-amber-900/60 text-amber-300';
    case 'cancelled':
    case 'skipped':
    case 'rolled_back':
      return 'bg-zinc-700 text-zinc-300';
    default:
      return 'bg-zinc-700 text-zinc-300';
  }
}

export default function SoftwareDeploymentPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>('packages');
  const [packages, setPackages] = useState<SoftwarePackage[]>([]);
  const [jobs, setJobs] = useState<DeploymentJob[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [showPkgForm, setShowPkgForm] = useState(false);
  const [showJobForm, setShowJobForm] = useState(false);
  const [pkgForm, setPkgForm] = useState({ ...emptyPkg });

  const [jobForm, setJobForm] = useState({
    package_id: '',
    name: '',
    action: 'install',
    hostnames: '',
    device_ids: [] as string[],
    notes: '',
  });

  const [selectedJob, setSelectedJob] = useState<DeploymentJob | null>(null);
  const [summary, setSummary] = useState<DeploymentJobSummary | null>(null);
  const [events, setEvents] = useState<DeploymentEvent[]>([]);

  const flash = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 2500);
  };

  const loadData = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [p, j, d] = await Promise.all([
        listPackages(),
        listDeploymentJobs(),
        getDevices().catch(() => [] as Device[]),
      ]);
      setPackages(p);
      setJobs(j);
      setDevices(d);
    } catch (e: any) {
      setError(e?.message || 'Failed to load software deployment data');
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

  const selectJob = async (job: DeploymentJob) => {
    setSelectedJob(job);
    try {
      const [s, ev] = await Promise.all([
        getDeploymentSummary(job.id),
        listDeploymentEvents(job.id),
      ]);
      setSummary(s);
      setEvents(ev);
    } catch (e: any) {
      setError(e?.message || 'Failed to load job detail');
    }
  };

  const savePackage = async () => {
    try {
      setBusy(true);
      setError(null);
      await createPackage({
        name: pkgForm.name,
        version: pkgForm.version || '1.0.0',
        publisher: pkgForm.publisher || null,
        description: pkgForm.description || null,
        package_type: pkgForm.package_type,
        source_url: pkgForm.source_url || null,
        file_name: pkgForm.file_name || null,
        sha256: pkgForm.sha256 || null,
        choco_id: pkgForm.choco_id || null,
        winget_id: pkgForm.winget_id || null,
        install_args: pkgForm.install_args || null,
        uninstall_args: pkgForm.uninstall_args || null,
        uninstall_command: pkgForm.uninstall_command || null,
        requires_reboot: pkgForm.requires_reboot,
        requires_elevation: pkgForm.requires_elevation,
        timeout_seconds: Number(pkgForm.timeout_seconds) || 3600,
        architecture: pkgForm.architecture || 'any',
        is_active: true,
        success_exit_codes: [0],
      });
      flash('Package added to repository');
      setShowPkgForm(false);
      setPkgForm({ ...emptyPkg });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to create package');
    } finally {
      setBusy(false);
    }
  };

  const removePackage = async (id: string) => {
    if (!confirm('Delete or deactivate this package?')) return;
    try {
      await deletePackage(id);
      flash('Package removed');
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to delete package');
    }
  };

  const saveJob = async () => {
    try {
      setBusy(true);
      setError(null);
      const hostnames = jobForm.hostnames
        .split(/[,\n]/)
        .map((s) => s.trim())
        .filter(Boolean);
      const created = await createDeploymentJob({
        package_id: jobForm.package_id,
        name: jobForm.name,
        action: jobForm.action,
        device_ids: jobForm.device_ids,
        hostnames,
        notes: jobForm.notes || null,
        created_by: user?.email || null,
      });
      flash('Deployment job created');
      setShowJobForm(false);
      setJobForm({
        package_id: '',
        name: '',
        action: 'install',
        hostnames: '',
        device_ids: [],
        notes: '',
      });
      await loadData();
      await selectJob(created);
      setTab('jobs');
    } catch (e: any) {
      setError(e?.message || 'Failed to create job');
    } finally {
      setBusy(false);
    }
  };

  const onStart = async (job: DeploymentJob) => {
    try {
      const updated = await startDeploymentJob(job.id);
      flash('Job started');
      await loadData();
      await selectJob(updated);
    } catch (e: any) {
      setError(e?.message || 'Failed to start job');
    }
  };

  const onCancel = async (job: DeploymentJob) => {
    try {
      const updated = await cancelDeploymentJob(job.id);
      flash('Job cancelled');
      await loadData();
      await selectJob(updated);
    } catch (e: any) {
      setError(e?.message || 'Failed to cancel job');
    }
  };

  const onRollback = async (job: DeploymentJob) => {
    if (!confirm('Create a rollback job for all successful targets?')) return;
    try {
      const rb = await rollbackDeploymentJob(job.id, {
        created_by: user?.email || undefined,
      });
      flash('Rollback job created');
      await loadData();
      await selectJob(rb);
      setTab('jobs');
    } catch (e: any) {
      setError(e?.message || 'Failed to create rollback');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0f1c] flex items-center justify-center text-white">
        Loading Software Deployment...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white">
      <div className="max-w-7xl mx-auto p-8">
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
                <Download className="text-sky-400" /> Software Deployment
              </h1>
              <p className="text-zinc-400 text-sm mt-1">
                Application repository · MSI/EXE · Chocolatey · Winget · Rollback · Success reporting
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
            {tab === 'packages' ? (
              <button
                onClick={() => {
                  setPkgForm({ ...emptyPkg });
                  setShowPkgForm(true);
                }}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium"
              >
                <Plus size={18} /> Add Package
              </button>
            ) : (
              <button
                onClick={() => setShowJobForm(true)}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium"
              >
                <Plus size={18} /> New Job
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

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setTab('packages')}
            className={`px-5 py-2.5 rounded-xl text-sm font-medium transition ${
              tab === 'packages'
                ? 'bg-sky-600 text-white'
                : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
            }`}
          >
            Repository ({packages.length})
          </button>
          <button
            onClick={() => setTab('jobs')}
            className={`px-5 py-2.5 rounded-xl text-sm font-medium transition ${
              tab === 'jobs'
                ? 'bg-sky-600 text-white'
                : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
            }`}
          >
            Jobs ({jobs.length})
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            {tab === 'packages' && (
              <>
                {packages.length === 0 && !busy && (
                  <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                    No packages in the repository yet.
                  </div>
                )}
                {packages.map((pkg) => (
                  <div
                    key={pkg.id}
                    className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-3 mb-1">
                        <Package size={18} className="text-sky-400" />
                        <h3 className="text-lg font-semibold">{pkg.name}</h3>
                        <span className="text-xs text-zinc-400">v{pkg.version}</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-sky-300">
                          {pkg.package_type}
                        </span>
                        {!pkg.is_active && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-700 text-zinc-400">
                            inactive
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-3 text-xs text-zinc-400">
                        {pkg.publisher && <span>{pkg.publisher}</span>}
                        {pkg.choco_id && <span>choco:{pkg.choco_id}</span>}
                        {pkg.winget_id && <span>winget:{pkg.winget_id}</span>}
                        {pkg.file_name && <span>{pkg.file_name}</span>}
                        {pkg.requires_reboot && <span className="text-amber-400">reboot</span>}
                      </div>
                    </div>
                    <button
                      onClick={() => removePackage(pkg.id)}
                      className="p-2 rounded-xl bg-zinc-800 hover:bg-red-900/40 text-red-400"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </>
            )}

            {tab === 'jobs' && (
              <>
                {jobs.length === 0 && !busy && (
                  <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                    No deployment jobs yet.
                  </div>
                )}
                {jobs.map((job) => (
                  <div
                    key={job.id}
                    onClick={() => selectJob(job)}
                    className={`bg-zinc-900 border rounded-3xl p-6 cursor-pointer transition ${
                      selectedJob?.id === job.id
                        ? 'border-sky-500'
                        : 'border-zinc-700 hover:border-zinc-500'
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold">{job.name}</h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(job.status)}`}>
                            {job.status}
                          </span>
                          <span className="text-xs text-zinc-400">{job.action}</span>
                        </div>
                        <div className="text-xs text-zinc-400">
                          Targets {job.targets_success}/{job.targets_total} ok ·{' '}
                          {job.targets_failed} failed · {job.targets_pending} pending
                          {job.rollback_of_job_id && (
                            <span className="text-amber-300"> · rollback</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        {(job.status === 'queued' || job.status === 'pending') && (
                          <button
                            onClick={() => onStart(job)}
                            className="p-2 rounded-xl bg-emerald-900/40 hover:bg-emerald-800/50 text-emerald-300"
                            title="Start"
                          >
                            <Play size={18} />
                          </button>
                        )}
                        {['queued', 'running', 'pending'].includes(job.status) && (
                          <button
                            onClick={() => onCancel(job)}
                            className="p-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                            title="Cancel"
                          >
                            <Square size={18} />
                          </button>
                        )}
                        {job.status === 'completed' && job.targets_success > 0 && (
                          <button
                            onClick={() => onRollback(job)}
                            className="p-2 rounded-xl bg-amber-900/40 hover:bg-amber-800/50 text-amber-300"
                            title="Rollback"
                          >
                            <RotateCcw size={18} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>

          <div className="xl:col-span-1">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 sticky top-8 space-y-5">
              {!selectedJob ? (
                <p className="text-zinc-500 text-sm text-center py-10">
                  Select a job for success reporting, targets, and event timeline.
                </p>
              ) : (
                <>
                  <div>
                    <h3 className="text-lg font-semibold">{selectedJob.name}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(selectedJob.status)}`}>
                      {selectedJob.status}
                    </span>
                  </div>

                  {summary && (
                    <div className="bg-zinc-800/60 rounded-2xl p-4 text-sm space-y-1">
                      <div className="font-medium mb-1">Success report</div>
                      <div className="text-xs text-zinc-400">
                        Success rate: <span className="text-sky-300">{summary.success_rate}%</span>
                      </div>
                      <div className="text-xs text-zinc-400">
                        {summary.targets_success} ok · {summary.targets_failed} failed ·{' '}
                        {summary.targets_pending} pending / {summary.targets_total}
                      </div>
                    </div>
                  )}

                  <div>
                    <div className="font-medium text-sm mb-2">Targets</div>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {(selectedJob.targets || []).length === 0 && (
                        <p className="text-xs text-zinc-500">No targets</p>
                      )}
                      {(selectedJob.targets || []).map((t) => (
                        <div
                          key={t.id}
                          className="text-xs bg-zinc-800/50 border border-zinc-700 rounded-xl px-3 py-2"
                        >
                          <div className="flex justify-between">
                            <span>{t.hostname || t.device_id?.slice(0, 8) || t.id.slice(0, 8)}</span>
                            <span className={statusColor(t.status).replace('bg-', 'text-').split(' ')[1] || ''}>
                              {t.status}
                            </span>
                          </div>
                          {t.exit_code != null && (
                            <div className="text-zinc-500">exit {t.exit_code}</div>
                          )}
                          {t.error_message && (
                            <div className="text-red-400 truncate">{t.error_message}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="font-medium text-sm mb-2">Events</div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {events.length === 0 && (
                        <p className="text-xs text-zinc-500">No events</p>
                      )}
                      {events.map((ev) => (
                        <div
                          key={ev.id}
                          className="text-xs bg-zinc-800/50 border border-zinc-700 rounded-xl px-3 py-2"
                        >
                          <span
                            className={
                              ev.level === 'error'
                                ? 'text-red-400'
                                : ev.level === 'warning'
                                  ? 'text-amber-300'
                                  : 'text-zinc-400'
                            }
                          >
                            [{ev.level}]
                          </span>{' '}
                          {ev.message}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Package modal */}
        {showPkgForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">Add Package</h2>
                <button onClick={() => setShowPkgForm(false)} className="p-2 hover:bg-zinc-800 rounded-xl">
                  <X size={20} />
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="text-xs text-zinc-400">Name *</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.name}
                    onChange={(e) => setPkgForm({ ...pkgForm, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Version</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.version}
                    onChange={(e) => setPkgForm({ ...pkgForm, version: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Type *</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.package_type}
                    onChange={(e) => setPkgForm({ ...pkgForm, package_type: e.target.value })}
                  >
                    {PACKAGE_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Publisher</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.publisher}
                    onChange={(e) => setPkgForm({ ...pkgForm, publisher: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Source URL (MSI/EXE/custom)</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.source_url}
                    onChange={(e) => setPkgForm({ ...pkgForm, source_url: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Chocolatey ID</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.choco_id}
                    onChange={(e) => setPkgForm({ ...pkgForm, choco_id: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Winget ID</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.winget_id}
                    onChange={(e) => setPkgForm({ ...pkgForm, winget_id: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Install args</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    placeholder="/quiet /norestart"
                    value={pkgForm.install_args}
                    onChange={(e) => setPkgForm({ ...pkgForm, install_args: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Uninstall command (rollback)</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={pkgForm.uninstall_command}
                    onChange={(e) => setPkgForm({ ...pkgForm, uninstall_command: e.target.value })}
                  />
                </div>
                <div className="md:col-span-2 flex flex-wrap gap-4 text-sm">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={pkgForm.requires_elevation}
                      onChange={(e) =>
                        setPkgForm({ ...pkgForm, requires_elevation: e.target.checked })
                      }
                    />
                    Elevation
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={pkgForm.requires_reboot}
                      onChange={(e) =>
                        setPkgForm({ ...pkgForm, requires_reboot: e.target.checked })
                      }
                    />
                    May require reboot
                  </label>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowPkgForm(false)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={savePackage}
                  disabled={!pkgForm.name || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Save Package
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Job modal */}
        {showJobForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-xl max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">New Deployment Job</h2>
                <button onClick={() => setShowJobForm(false)} className="p-2 hover:bg-zinc-800 rounded-xl">
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-400">Job name *</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={jobForm.name}
                    onChange={(e) => setJobForm({ ...jobForm, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Package *</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={jobForm.package_id}
                    onChange={(e) => setJobForm({ ...jobForm, package_id: e.target.value })}
                  >
                    <option value="">Select package…</option>
                    {packages
                      .filter((p) => p.is_active)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} v{p.version} ({p.package_type})
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Action</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={jobForm.action}
                    onChange={(e) => setJobForm({ ...jobForm, action: e.target.value })}
                  >
                    <option value="install">install</option>
                    <option value="uninstall">uninstall</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Hostnames (comma or newline)</label>
                  <textarea
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm min-h-[72px]"
                    value={jobForm.hostnames}
                    onChange={(e) => setJobForm({ ...jobForm, hostnames: e.target.value })}
                    placeholder="pc-01.local, pc-02.local"
                  />
                </div>
                {devices.length > 0 && (
                  <div>
                    <label className="text-xs text-zinc-400">Devices</label>
                    <select
                      multiple
                      className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm min-h-[100px]"
                      value={jobForm.device_ids}
                      onChange={(e) =>
                        setJobForm({
                          ...jobForm,
                          device_ids: Array.from(e.target.selectedOptions).map((o) => o.value),
                        })
                      }
                    >
                      {devices.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.hostname || d.name || d.id}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="text-xs text-zinc-400">Notes</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={jobForm.notes}
                    onChange={(e) => setJobForm({ ...jobForm, notes: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowJobForm(false)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={saveJob}
                  disabled={!jobForm.name || !jobForm.package_id || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Create Job
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
