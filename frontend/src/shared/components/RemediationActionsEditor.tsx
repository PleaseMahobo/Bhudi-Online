'use client';

import React from 'react';
import { Plus, Trash2, Zap } from 'lucide-react';

export type RemediationActionForm = {
  name: string;
  type: 'run_script' | 'run_command' | 'inventory_refresh' | 'notify_only';
  enabled: boolean;
  shell: string;
  script_content: string;
  command_type: string;
  min_severity: 'info' | 'warning' | 'critical' | 'emergency';
  cooldown_seconds: number;
  dry_run: boolean;
  ignore_suppression: boolean;
};

export const emptyRemediationAction = (): RemediationActionForm => ({
  name: '',
  type: 'run_script',
  enabled: true,
  shell: 'powershell',
  script_content: '',
  command_type: '',
  min_severity: 'warning',
  cooldown_seconds: 900,
  dry_run: false,
  ignore_suppression: false,
});

export default function RemediationActionsEditor({
  value,
  onChange,
}: {
  value: RemediationActionForm[];
  onChange: (next: RemediationActionForm[]) => void;
}) {
  const update = (index: number, patch: Partial<RemediationActionForm>) => {
    const next = value.map((row, i) => (i === index ? { ...row, ...patch } : row));
    onChange(next);
  };

  const remove = (index: number) => onChange(value.filter((_, i) => i !== index));

  const add = () => onChange([...value, emptyRemediationAction()]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Zap size={16} className="text-indigo-600" />
          Remediation actions
        </div>
        <button
          type="button"
          onClick={add}
          className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
        >
          <Plus size={14} /> Add action
        </button>
      </div>
      <p className="text-xs text-slate-500">
        When this rule fires, Bhudi queues these actions on the matched device (with cooldown and
        severity gates). Use dry-run to log intent without executing.
      </p>

      {value.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
          No remediation actions. Alerts will only notify via escalation policy.
        </div>
      )}

      {value.map((action, index) => (
        <div
          key={index}
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="grid flex-1 gap-3 sm:grid-cols-2">
              <label className="block text-xs font-medium text-slate-600">
                Name
                <input
                  className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
                  value={action.name}
                  onChange={(e) => update(index, { name: e.target.value })}
                  placeholder="Restart spooler"
                />
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Type
                <select
                  className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
                  value={action.type}
                  onChange={(e) =>
                    update(index, {
                      type: e.target.value as RemediationActionForm['type'],
                    })
                  }
                >
                  <option value="run_script">Run script</option>
                  <option value="run_command">Run command</option>
                  <option value="inventory_refresh">Inventory refresh</option>
                  <option value="notify_only">Notify only (no exec)</option>
                </select>
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Shell
                <select
                  className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
                  value={action.shell}
                  onChange={(e) => update(index, { shell: e.target.value })}
                >
                  <option value="powershell">PowerShell</option>
                  <option value="bash">Bash</option>
                  <option value="sh">SH</option>
                  <option value="python">Python</option>
                  <option value="cmd">CMD</option>
                </select>
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Min severity
                <select
                  className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
                  value={action.min_severity}
                  onChange={(e) =>
                    update(index, {
                      min_severity: e.target.value as RemediationActionForm['min_severity'],
                    })
                  }
                >
                  <option value="info">info</option>
                  <option value="warning">warning</option>
                  <option value="critical">critical</option>
                  <option value="emergency">emergency</option>
                </select>
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Cooldown (seconds)
                <input
                  type="number"
                  min={0}
                  max={86400}
                  className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
                  value={action.cooldown_seconds}
                  onChange={(e) =>
                    update(index, { cooldown_seconds: Number(e.target.value) || 0 })
                  }
                />
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Command type (optional)
                <input
                  className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
                  value={action.command_type}
                  onChange={(e) => update(index, { command_type: e.target.value })}
                  placeholder="service_restart"
                />
              </label>
            </div>
            <button
              type="button"
              onClick={() => remove(index)}
              className="rounded-lg p-2 text-red-500 hover:bg-red-50"
              title="Remove action"
            >
              <Trash2 size={16} />
            </button>
          </div>

          {(action.type === 'run_script' || action.type === 'run_command') && (
            <label className="block text-xs font-medium text-slate-600">
              Script / command
              <textarea
                rows={5}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-950 p-3 font-mono text-xs text-slate-100"
                value={action.script_content}
                onChange={(e) => update(index, { script_content: e.target.value })}
                placeholder={
                  action.shell === 'powershell'
                    ? 'Restart-Service -Name Spooler -Force'
                    : 'systemctl restart cups || true'
                }
              />
            </label>
          )}

          <div className="flex flex-wrap gap-4 text-xs text-slate-600">
            <label className="inline-flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={action.enabled}
                onChange={(e) => update(index, { enabled: e.target.checked })}
              />
              Enabled
            </label>
            <label className="inline-flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={action.dry_run}
                onChange={(e) => update(index, { dry_run: e.target.checked })}
              />
              Dry run
            </label>
            <label className="inline-flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={action.ignore_suppression}
                onChange={(e) => update(index, { ignore_suppression: e.target.checked })}
              />
              Ignore suppression
            </label>
          </div>
        </div>
      ))}
    </div>
  );
}
