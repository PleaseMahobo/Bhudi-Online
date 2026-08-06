'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { useRouter } from 'next/navigation';
import {
  listAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  listEscalationPolicies,
  createEscalationPolicy,
  updateEscalationPolicy,
  deleteEscalationPolicy,
  type AlertRule,
  type EscalationPolicy,
  type EscalationLevel,
} from '@/lib/api';
import LiveAlertStream from '@/shared/components/LiveAlertStream';
import {
  Bell,
  Plus,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Shield,
  ArrowLeft,
  Save,
  X,
} from 'lucide-react';

type Tab = 'rules' | 'policies';

const emptyRule = {
  name: '',
  description: '',
  provider: '',
  check_type: '',
  target: '',
  metric_name: '',
  warning_threshold: null as number | null,
  critical_threshold: null as number | null,
  anomaly_enabled: false,
  anomaly_tolerance: null as number | null,
  state_change_enabled: true,
  ai_suppression_enabled: true,
  maintenance_window_name: '',
  escalation_policy_id: null as string | null,
  enabled: true,
  priority: 100,
  tags: null,
};

const emptyPolicy = {
  name: '',
  description: '',
  levels: [{ repeat_count: 1, severity: 'warning', notify: ['email'] }] as EscalationLevel[],
  enabled: true,
};

export default function AlertEnginePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>('rules');
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [policies, setPolicies] = useState<EscalationPolicy[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [showRuleForm, setShowRuleForm] = useState(false);
  const [showPolicyForm, setShowPolicyForm] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [editingPolicyId, setEditingPolicyId] = useState<string | null>(null);

  const [ruleForm, setRuleForm] = useState({ ...emptyRule });
  const [policyForm, setPolicyForm] = useState({ ...emptyPolicy });

  const loadData = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [r, p] = await Promise.all([listAlertRules(), listEscalationPolicies()]);
      setRules(r);
      setPolicies(p);
    } catch (e: any) {
      setError(e?.message || 'Failed to load alert engine data');
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

  const flash = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 2500);
  };

  const openCreateRule = () => {
    setEditingRuleId(null);
    setRuleForm({ ...emptyRule });
    setShowRuleForm(true);
  };

  const openEditRule = (rule: AlertRule) => {
    setEditingRuleId(rule.id);
    setRuleForm({
      name: rule.name,
      description: rule.description || '',
      provider: rule.provider || '',
      check_type: rule.check_type || '',
      target: rule.target || '',
      metric_name: rule.metric_name || '',
      warning_threshold: rule.warning_threshold ?? null,
      critical_threshold: rule.critical_threshold ?? null,
      anomaly_enabled: rule.anomaly_enabled,
      anomaly_tolerance: rule.anomaly_tolerance ?? null,
      state_change_enabled: rule.state_change_enabled,
      ai_suppression_enabled: rule.ai_suppression_enabled,
      maintenance_window_name: rule.maintenance_window_name || '',
      escalation_policy_id: rule.escalation_policy_id || null,
      enabled: rule.enabled,
      priority: rule.priority,
      tags: rule.tags || null,
    });
    setShowRuleForm(true);
  };

  const saveRule = async () => {
    try {
      setBusy(true);
      setError(null);
      const payload = {
        ...ruleForm,
        description: ruleForm.description || null,
        provider: ruleForm.provider || null,
        check_type: ruleForm.check_type || null,
        target: ruleForm.target || null,
        metric_name: ruleForm.metric_name || null,
        maintenance_window_name: ruleForm.maintenance_window_name || null,
      };
      if (editingRuleId) {
        await updateAlertRule(editingRuleId, payload);
        flash('Alert rule updated');
      } else {
        await createAlertRule(payload);
        flash('Alert rule created');
      }
      setShowRuleForm(false);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to save rule');
    } finally {
      setBusy(false);
    }
  };

  const toggleRule = async (rule: AlertRule) => {
    try {
      await updateAlertRule(rule.id, { enabled: !rule.enabled });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to toggle rule');
    }
  };

  const removeRule = async (id: string) => {
    if (!confirm('Delete this alert rule?')) return;
    try {
      await deleteAlertRule(id);
      flash('Alert rule deleted');
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to delete rule');
    }
  };

  const openCreatePolicy = () => {
    setEditingPolicyId(null);
    setPolicyForm({
      ...emptyPolicy,
      levels: [{ repeat_count: 1, severity: 'warning', notify: ['email'] }],
    });
    setShowPolicyForm(true);
  };

  const openEditPolicy = (policy: EscalationPolicy) => {
    setEditingPolicyId(policy.id);
    setPolicyForm({
      name: policy.name,
      description: policy.description || '',
      levels: policy.levels.length
        ? policy.levels
        : [{ repeat_count: 1, severity: 'warning', notify: ['email'] }],
      enabled: policy.enabled,
    });
    setShowPolicyForm(true);
  };

  const savePolicy = async () => {
    try {
      setBusy(true);
      setError(null);
      const payload = {
        ...policyForm,
        description: policyForm.description || null,
      };
      if (editingPolicyId) {
        await updateEscalationPolicy(editingPolicyId, payload);
        flash('Escalation policy updated');
      } else {
        await createEscalationPolicy(payload);
        flash('Escalation policy created');
      }
      setShowPolicyForm(false);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to save policy');
    } finally {
      setBusy(false);
    }
  };

  const togglePolicy = async (policy: EscalationPolicy) => {
    try {
      await updateEscalationPolicy(policy.id, { enabled: !policy.enabled });
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to toggle policy');
    }
  };

  const removePolicy = async (id: string) => {
    if (!confirm('Delete this escalation policy?')) return;
    try {
      await deleteEscalationPolicy(id);
      flash('Escalation policy deleted');
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to delete policy');
    }
  };

  const updateLevel = (index: number, field: keyof EscalationLevel, value: any) => {
    const levels = [...policyForm.levels];
    levels[index] = { ...levels[index], [field]: value };
    setPolicyForm({ ...policyForm, levels });
  };

  const addLevel = () => {
    setPolicyForm({
      ...policyForm,
      levels: [
        ...policyForm.levels,
        {
          repeat_count: policyForm.levels.length + 1,
          severity: 'critical',
          notify: ['email'],
        },
      ],
    });
  };

  const removeLevel = (index: number) => {
    setPolicyForm({
      ...policyForm,
      levels: policyForm.levels.filter((_, i) => i !== index),
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0f1c] flex items-center justify-center text-white">
        Loading Alert Engine...
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
                <Bell className="text-sky-400" /> Alert Engine
              </h1>
              <p className="text-zinc-400 text-sm mt-1">
                Rules, escalation policies & real-time alert stream
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            {tab === 'rules' ? (
              <button
                onClick={openCreateRule}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium transition"
              >
                <Plus size={18} /> New Rule
              </button>
            ) : (
              <button
                onClick={openCreatePolicy}
                className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 px-4 py-2.5 rounded-xl font-medium transition"
              >
                <Plus size={18} /> New Policy
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

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setTab('rules')}
                className={`px-5 py-2.5 rounded-xl text-sm font-medium transition ${
                  tab === 'rules'
                    ? 'bg-sky-600 text-white'
                    : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
                }`}
              >
                Alert Rules ({rules.length})
              </button>
              <button
                onClick={() => setTab('policies')}
                className={`px-5 py-2.5 rounded-xl text-sm font-medium transition ${
                  tab === 'policies'
                    ? 'bg-sky-600 text-white'
                    : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
                }`}
              >
                Escalation Policies ({policies.length})
              </button>
            </div>

            {tab === 'rules' && (
              <div className="space-y-4">
                {rules.length === 0 && !busy && (
                  <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                    No alert rules yet. Create your first production rule.
                  </div>
                )}
                {rules.map((rule) => (
                  <div
                    key={rule.id}
                    className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-lg font-semibold">{rule.name}</h3>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            rule.enabled
                              ? 'bg-emerald-900/60 text-emerald-400'
                              : 'bg-zinc-700 text-zinc-400'
                          }`}
                        >
                          {rule.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <span className="text-xs text-zinc-500">Priority {rule.priority}</span>
                      </div>
                      {rule.description && (
                        <p className="text-sm text-zinc-400 mb-2">{rule.description}</p>
                      )}
                      <div className="flex flex-wrap gap-3 text-xs text-zinc-400">
                        {rule.provider && <span>Provider: {rule.provider}</span>}
                        {rule.check_type && <span>Check: {rule.check_type}</span>}
                        {rule.metric_name && <span>Metric: {rule.metric_name}</span>}
                        {rule.warning_threshold != null && (
                          <span className="text-yellow-400">Warn ≥ {rule.warning_threshold}</span>
                        )}
                        {rule.critical_threshold != null && (
                          <span className="text-red-400">Crit ≥ {rule.critical_threshold}</span>
                        )}
                        {rule.anomaly_enabled && (
                          <span className="text-purple-400">Anomaly</span>
                        )}
                        {rule.ai_suppression_enabled && (
                          <span className="text-sky-400">AI Suppression</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleRule(rule)}
                        className="p-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
                      >
                        {rule.enabled ? (
                          <ToggleRight size={22} className="text-emerald-400" />
                        ) : (
                          <ToggleLeft size={22} className="text-zinc-500" />
                        )}
                      </button>
                      <button
                        onClick={() => openEditRule(rule)}
                        className="px-3 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-sm transition"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => removeRule(rule.id)}
                        className="p-2 rounded-xl bg-zinc-800 hover:bg-red-900/40 text-red-400 transition"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'policies' && (
              <div className="space-y-4">
                {policies.length === 0 && !busy && (
                  <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-10 text-center text-zinc-400">
                    No escalation policies yet.
                  </div>
                )}
                {policies.map((policy) => (
                  <div
                    key={policy.id}
                    className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <Shield size={18} className="text-sky-400" />
                        <h3 className="text-lg font-semibold">{policy.name}</h3>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            policy.enabled
                              ? 'bg-emerald-900/60 text-emerald-400'
                              : 'bg-zinc-700 text-zinc-400'
                          }`}
                        >
                          {policy.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      {policy.description && (
                        <p className="text-sm text-zinc-400 mb-2">{policy.description}</p>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {policy.levels.map((lvl, i) => (
                          <span
                            key={i}
                            className="text-xs bg-zinc-800 border border-zinc-600 px-2 py-1 rounded-lg text-zinc-300"
                          >
                            L{i + 1}: ×{lvl.repeat_count} → {lvl.severity} ({lvl.notify.join(', ')})
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => togglePolicy(policy)}
                        className="p-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
                      >
                        {policy.enabled ? (
                          <ToggleRight size={22} className="text-emerald-400" />
                        ) : (
                          <ToggleLeft size={22} className="text-zinc-500" />
                        )}
                      </button>
                      <button
                        onClick={() => openEditPolicy(policy)}
                        className="px-3 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-sm transition"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => removePolicy(policy.id)}
                        className="p-2 rounded-xl bg-zinc-800 hover:bg-red-900/40 text-red-400 transition"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Live WebSocket stream */}
          <div className="xl:col-span-1">
            <LiveAlertStream />
          </div>
        </div>

        {/* Modals kept identical - rule form */}
        {showRuleForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">
                  {editingRuleId ? 'Edit Alert Rule' : 'Create Alert Rule'}
                </h2>
                <button
                  onClick={() => setShowRuleForm(false)}
                  className="p-2 hover:bg-zinc-800 rounded-xl"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="text-xs text-zinc-400">Name *</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                    value={ruleForm.name}
                    onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-zinc-400">Description</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                    value={ruleForm.description}
                    onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Provider</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.provider}
                    onChange={(e) => setRuleForm({ ...ruleForm, provider: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Check Type</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.check_type}
                    onChange={(e) => setRuleForm({ ...ruleForm, check_type: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Target</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.target}
                    onChange={(e) => setRuleForm({ ...ruleForm, target: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Metric Name</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.metric_name}
                    onChange={(e) => setRuleForm({ ...ruleForm, metric_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Warning Threshold</label>
                  <input
                    type="number"
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.warning_threshold ?? ''}
                    onChange={(e) =>
                      setRuleForm({
                        ...ruleForm,
                        warning_threshold: e.target.value === '' ? null : Number(e.target.value),
                      })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Critical Threshold</label>
                  <input
                    type="number"
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.critical_threshold ?? ''}
                    onChange={(e) =>
                      setRuleForm({
                        ...ruleForm,
                        critical_threshold: e.target.value === '' ? null : Number(e.target.value),
                      })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Anomaly Tolerance</label>
                  <input
                    type="number"
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.anomaly_tolerance ?? ''}
                    onChange={(e) =>
                      setRuleForm({
                        ...ruleForm,
                        anomaly_tolerance: e.target.value === '' ? null : Number(e.target.value),
                      })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Priority</label>
                  <input
                    type="number"
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.priority}
                    onChange={(e) => setRuleForm({ ...ruleForm, priority: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Maintenance Window</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.maintenance_window_name}
                    onChange={(e) =>
                      setRuleForm({ ...ruleForm, maintenance_window_name: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Escalation Policy</label>
                  <select
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={ruleForm.escalation_policy_id || ''}
                    onChange={(e) =>
                      setRuleForm({
                        ...ruleForm,
                        escalation_policy_id: e.target.value || null,
                      })
                    }
                  >
                    <option value="">None</option>
                    {policies.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex flex-wrap gap-4 mt-5 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={ruleForm.anomaly_enabled}
                    onChange={(e) => setRuleForm({ ...ruleForm, anomaly_enabled: e.target.checked })}
                  />
                  Anomaly
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={ruleForm.state_change_enabled}
                    onChange={(e) =>
                      setRuleForm({ ...ruleForm, state_change_enabled: e.target.checked })
                    }
                  />
                  State change
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={ruleForm.ai_suppression_enabled}
                    onChange={(e) =>
                      setRuleForm({ ...ruleForm, ai_suppression_enabled: e.target.checked })
                    }
                  />
                  AI suppression
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={ruleForm.enabled}
                    onChange={(e) => setRuleForm({ ...ruleForm, enabled: e.target.checked })}
                  />
                  Enabled
                </label>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowRuleForm(false)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={saveRule}
                  disabled={!ruleForm.name || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Save Rule
                </button>
              </div>
            </div>
          </div>
        )}

        {showPolicyForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">
                  {editingPolicyId ? 'Edit Escalation Policy' : 'Create Escalation Policy'}
                </h2>
                <button
                  onClick={() => setShowPolicyForm(false)}
                  className="p-2 hover:bg-zinc-800 rounded-xl"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-400">Name *</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={policyForm.name}
                    onChange={(e) => setPolicyForm({ ...policyForm, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-zinc-400">Description</label>
                  <input
                    className="w-full mt-1 bg-zinc-800 border border-zinc-600 rounded-xl px-4 py-2.5 text-sm"
                    value={policyForm.description}
                    onChange={(e) => setPolicyForm({ ...policyForm, description: e.target.value })}
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs text-zinc-400">Escalation Levels</label>
                    <button type="button" onClick={addLevel} className="text-xs text-sky-400">
                      + Add Level
                    </button>
                  </div>
                  <div className="space-y-3">
                    {policyForm.levels.map((level, i) => (
                      <div
                        key={i}
                        className="grid grid-cols-12 gap-2 items-center bg-zinc-800/60 border border-zinc-700 rounded-xl p-3"
                      >
                        <div className="col-span-3">
                          <label className="text-[10px] text-zinc-500">Repeat ≥</label>
                          <input
                            type="number"
                            min={1}
                            className="w-full bg-zinc-900 border border-zinc-600 rounded-lg px-2 py-1.5 text-sm"
                            value={level.repeat_count}
                            onChange={(e) =>
                              updateLevel(i, 'repeat_count', Number(e.target.value))
                            }
                          />
                        </div>
                        <div className="col-span-3">
                          <label className="text-[10px] text-zinc-500">Severity</label>
                          <select
                            className="w-full bg-zinc-900 border border-zinc-600 rounded-lg px-2 py-1.5 text-sm"
                            value={level.severity}
                            onChange={(e) => updateLevel(i, 'severity', e.target.value)}
                          >
                            <option value="info">info</option>
                            <option value="warning">warning</option>
                            <option value="critical">critical</option>
                          </select>
                        </div>
                        <div className="col-span-5">
                          <label className="text-[10px] text-zinc-500">Notify</label>
                          <input
                            className="w-full bg-zinc-900 border border-zinc-600 rounded-lg px-2 py-1.5 text-sm"
                            value={level.notify.join(', ')}
                            onChange={(e) =>
                              updateLevel(
                                i,
                                'notify',
                                e.target.value
                                  .split(',')
                                  .map((s) => s.trim())
                                  .filter(Boolean)
                              )
                            }
                          />
                        </div>
                        <div className="col-span-1 flex justify-end">
                          {policyForm.levels.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeLevel(i)}
                              className="p-1 text-red-400"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={policyForm.enabled}
                    onChange={(e) => setPolicyForm({ ...policyForm, enabled: e.target.checked })}
                  />
                  Enabled
                </label>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowPolicyForm(false)}
                  className="px-4 py-2.5 rounded-xl bg-zinc-800 text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={savePolicy}
                  disabled={!policyForm.name || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 text-sm font-medium disabled:opacity-50"
                >
                  <Save size={16} /> Save Policy
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
