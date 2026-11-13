'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  Clock3,
  Command,
  Loader2,
  Play,
  RefreshCw,
  Terminal,
  XCircle,
} from 'lucide-react';
import { getDevices } from '@/lib/api';
import MfaRequiredPanel from '@/shared/components/MfaRequiredPanel';
import { useMfaGate } from '@/shared/hooks/useMfaGate';

type Device = {
  id: string;
  device_id?: string;
  hostname?: string;
  name?: string;
  status?: string;
};

type CommandDefinition = {
  type: string;
  name: string;
  description: string;
  read_only: boolean;
  requires_confirmation?: boolean;
};

type QueueResult = {
  id: string;
  status: string;
  agent_id: string;
  command_type: string;
};

/** Local fallback so the library is never empty if the catalog API fails. */
const FALLBACK_CATALOG: CommandDefinition[] = [
  {
    type: 'inventory',
    name: 'Inventory',
    description: 'Collect operating system, hardware, network, and runtime inventory.',
    read_only: true,
  },
  {
    type: 'processes',
    name: 'Processes',
    description: 'List running processes and their resource ownership.',
    read_only: true,
  },
  {
    type: 'services',
    name: 'Services',
    description: 'List installed services and service state.',
    read_only: true,
  },
  {
    type: 'software',
    name: 'Software',
    description: 'Enumerate installed applications and packages.',
    read_only: true,
  },
  {
    type: 'windows_updates',
    name: 'Windows Updates',
    description: 'Collect installed Windows updates or package update status on supported platforms.',
    read_only: true,
  },
  {
    type: 'event_logs',
    name: 'Event Logs',
    description: 'Read recent operating-system event or journal entries.',
    read_only: true,
  },
  {
    type: 'network',
    name: 'Network',
    description: 'Collect interfaces, addresses, routes, DNS, and listening sockets where supported.',
    read_only: true,
  },
  {
    type: 'disks',
    name: 'Disks',
    description: 'Collect mounted disks, capacity, filesystem, and utilization.',
    read_only: true,
  },
  {
    type: 'printers',
    name: 'Printers',
    description: 'Enumerate printers, queues, status, and default printer information.',
    read_only: true,
  },
  {
    type: 'endpoint_security',
    name: 'Endpoint Security Scan',
    description: 'Run an endpoint security posture scan on the target agent.',
    read_only: true,
  },
  {
    type: 'remote_script',
    name: 'Remote Script',
    description: 'Execute an administrator-supplied script using an explicit interpreter.',
    read_only: false,
    requires_confirmation: true,
  },
  {
    type: 'remote_powershell',
    name: 'Remote PowerShell',
    description: 'Execute an administrator-supplied PowerShell command on a target agent.',
    read_only: false,
    requires_confirmation: true,
  },
];

const API_BASE = '';

function agentKey(d: Device): string {
  return String(d.device_id || d.id || '');
}

function deviceLabel(d: Device): string {
  return `${d.hostname || d.name || d.id} · ${d.status || 'unknown'}`;
}

export default function CommandCenter() {
  const { blocked: mfaBlocked } = useMfaGate();
  const [commands, setCommands] = useState<CommandDefinition[]>(FALLBACK_CATALOG);
  const [devices, setDevices] = useState<Device[]>([]);
  const [commandType, setCommandType] = useState('inventory');
  const [deviceId, setDeviceId] = useState('');
  const [script, setScript] = useState('');
  const [interpreter, setInterpreter] = useState('powershell');
  const [eventLogName, setEventLogName] = useState('Application');
  const [eventLogLimit, setEventLogLimit] = useState(100);
  const [timeoutSeconds, setTimeoutSeconds] = useState(300);
  const [queueResult, setQueueResult] = useState<QueueResult | null>(null);
  const [commandStatus, setCommandStatus] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [loadNote, setLoadNote] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadNote('');
    try {
      const [catalogRes, deviceRows] = await Promise.all([
        fetch(`${API_BASE}/api/v1/command-catalog`, {
          credentials: 'include',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        })
          .then(async (r) => {
            if (!r.ok) throw new Error(`catalog ${r.status}`);
            return r.json();
          })
          .catch(() => null),
        getDevices().catch(() => []),
      ]);

      const apiCommands = Array.isArray(catalogRes?.commands) ? catalogRes.commands : [];
      if (apiCommands.length > 0) {
        setCommands(apiCommands as CommandDefinition[]);
      } else {
        setCommands(FALLBACK_CATALOG);
        setLoadNote('Using built-in command library (catalog API unavailable).');
      }

      const rows = Array.isArray(deviceRows) ? (deviceRows as Device[]) : [];
      setDevices(rows);
      if (rows.length === 1 && !deviceId) {
        setDeviceId(agentKey(rows[0]));
      }
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const selected = useMemo(
    () => commands.find((c) => c.type === commandType) || FALLBACK_CATALOG.find((c) => c.type === commandType),
    [commands, commandType],
  );

  function buildPayload(): Record<string, unknown> {
    const payload: Record<string, unknown> = {};

    if (commandType === 'remote_script') {
      payload.script = script;
      payload.interpreter = interpreter;
      payload.timeout_seconds = timeoutSeconds;
    } else if (commandType === 'remote_powershell') {
      payload.command = script;
      payload.timeout_seconds = timeoutSeconds;
    } else if (commandType === 'event_logs') {
      payload.log_name = eventLogName || 'Application';
      payload.limit = Math.min(500, Math.max(1, Number(eventLogLimit) || 100));
    }

    return payload;
  }

  async function pollStatus(commandId: string) {
    setCommandStatus('queued');
    for (let i = 0; i < 12; i++) {
      await new Promise((r) => setTimeout(r, 2500));
      try {
        const res = await fetch(`${API_BASE}/api/v1/agent-commands/${commandId}`, {
          credentials: 'include',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        });
        if (!res.ok) {
          // Fallback: try listing by agent if single-command endpoint differs
          setCommandStatus((prev) => prev || 'queued');
          continue;
        }
        const data = await res.json();
        const status = String(data.status || data.state || '');
        if (status) setCommandStatus(status);
        if (['completed', 'success', 'failed', 'timed_out', 'cancelled', 'error'].includes(status.toLowerCase())) {
          break;
        }
      } catch {
        // keep polling
      }
    }
  }

  async function execute() {
    if (mfaBlocked) {
      setError('Enable MFA at /mfa/setup before running commands.');
      return;
    }
    const agentId = deviceId;
    if (!agentId) {
      setError('Select a target device.');
      return;
    }
    if (
      selected?.requires_confirmation &&
      !window.confirm(`Queue ${selected.name} on the selected device?`)
    ) {
      return;
    }
    if (
      (commandType === 'remote_script' || commandType === 'remote_powershell') &&
      !script.trim()
    ) {
      setError('Enter the command or script before queueing it.');
      return;
    }

    setBusy(true);
    setError('');
    setQueueResult(null);
    setCommandStatus('');

    try {
      const payload = buildPayload();

      const response = await fetch(`${API_BASE}/api/v1/commands`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        credentials: 'include',
        cache: 'no-store',
        body: JSON.stringify({
          agent_id: agentId,
          command_type: commandType,
          payload,
          priority: selected?.requires_confirmation ? 90 : 50,
          timeout_seconds: timeoutSeconds,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail =
          typeof data.detail === 'string'
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ')
              : data.message || 'Command could not be queued';
        throw new Error(detail);
      }

      const result = data as QueueResult;
      setQueueResult(result);
      setCommandStatus(result.status || 'queued');

      if (result.id) {
        void pollStatus(String(result.id));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Command could not be queued');
    } finally {
      setBusy(false);
    }
  }

  const needsScript = commandType === 'remote_script' || commandType === 'remote_powershell';
  const needsEventLogOpts = commandType === 'event_logs';

  return (
    <div className="space-y-6">
      {mfaBlocked ? <MfaRequiredPanel title="Command execution locked" /> : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          Select a library action, choose a target agent, then queue the operation.
        </p>
        <button
          type="button"
          onClick={() => void loadData()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh devices & catalog
        </button>
      </div>

      {loadNote ? (
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{loadNote}</div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Command size={17} className="text-indigo-600" />
            Command library
          </div>
          <div className="mt-4 max-h-[28rem] space-y-1 overflow-y-auto">
            {commands.map((command) => (
              <button
                key={command.type}
                type="button"
                onClick={() => {
                  setCommandType(command.type);
                  setQueueResult(null);
                  setCommandStatus('');
                  setError('');
                }}
                className={
                  'w-full rounded-lg px-3 py-2 text-left text-sm ' +
                  (command.type === commandType
                    ? 'bg-indigo-50 font-semibold text-indigo-700'
                    : 'text-slate-600 hover:bg-slate-50')
                }
              >
                <span className="block">{command.name}</span>
                <span className="mt-0.5 block text-[11px] font-normal text-slate-400">
                  {command.read_only ? 'Read only' : 'Action'}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-lg font-semibold text-slate-900">{selected?.name || commandType}</p>
              <p className="mt-1 text-sm text-slate-500">{selected?.description}</p>
            </div>
            {selected?.read_only ? (
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                Read only
              </span>
            ) : (
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                Action
              </span>
            )}
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">
              Target agent
              <select
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"
              >
                <option value="">Select device</option>
                {devices.map((d) => (
                  <option key={agentKey(d)} value={agentKey(d)}>
                    {deviceLabel(d)}
                  </option>
                ))}
              </select>
              {devices.length === 0 && !loading ? (
                <span className="mt-1 block text-xs text-amber-600">
                  No devices found. Enroll an agent, then refresh.
                </span>
              ) : null}
            </label>

            {commandType === 'remote_script' ? (
              <label className="block text-sm font-medium text-slate-700">
                Interpreter
                <select
                  value={interpreter}
                  onChange={(e) => setInterpreter(e.target.value)}
                  className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"
                >
                  <option value="powershell">PowerShell</option>
                  <option value="bash">Bash</option>
                  <option value="sh">SH</option>
                  <option value="python">Python</option>
                </select>
              </label>
            ) : (
              <label className="block text-sm font-medium text-slate-700">
                Timeout (seconds)
                <input
                  type="number"
                  min={30}
                  max={3600}
                  value={timeoutSeconds}
                  onChange={(e) => setTimeoutSeconds(Number(e.target.value) || 300)}
                  className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"
                />
              </label>
            )}
          </div>

          {needsEventLogOpts ? (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-medium text-slate-700">
                Log name
                <select
                  value={eventLogName}
                  onChange={(e) => setEventLogName(e.target.value)}
                  className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"
                >
                  <option value="Application">Application</option>
                  <option value="System">System</option>
                  <option value="Security">Security</option>
                </select>
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Entry limit
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={eventLogLimit}
                  onChange={(e) => setEventLogLimit(Number(e.target.value) || 100)}
                  className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"
                />
              </label>
            </div>
          ) : null}

          {needsScript ? (
            <label className="mt-4 block text-sm font-medium text-slate-700">
              {commandType === 'remote_powershell' ? 'PowerShell command' : 'Script'}
              <textarea
                value={script}
                onChange={(e) => setScript(e.target.value)}
                rows={9}
                className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-950 p-4 font-mono text-sm text-slate-100 outline-none focus:ring-2 focus:ring-indigo-200"
                placeholder={
                  commandType === 'remote_powershell'
                    ? 'Get-Service | Where-Object Status -eq Running'
                    : '# enter your script'
                }
              />
            </label>
          ) : null}

          {error ? (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <XCircle size={16} />
              {error}
            </div>
          ) : null}

          {queueResult ? (
            <div className="mt-4 space-y-1 rounded-lg bg-emerald-50 px-3 py-3 text-sm text-emerald-800">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={17} />
                <b>Command queued.</b>
              </div>
              <div className="text-xs">ID: {queueResult.id}</div>
              <div className="text-xs">Type: {queueResult.command_type || commandType}</div>
              {commandStatus ? (
                <div className="text-xs">Status: {commandStatus}</div>
              ) : null}
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => void execute()}
            disabled={busy || !deviceId || mfaBlocked || loading}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {busy ? 'Queueing…' : `Run ${selected?.name || 'Command'}`}
          </button>
        </section>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-sm font-semibold">
          <Terminal size={17} className="text-indigo-600" />
          Command lifecycle
        </header>
        <div className="grid gap-4 p-5 sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-4">
            <Clock3 className="text-indigo-500" size={18} />
            <p className="mt-3 text-sm font-semibold">Queued</p>
            <p className="mt-1 text-xs text-slate-500">
              The server has accepted the command for the selected agent.
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <Loader2 className="text-amber-500" size={18} />
            <p className="mt-3 text-sm font-semibold">Dispatched</p>
            <p className="mt-1 text-xs text-slate-500">
              The agent polls and receives pending commands.
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <CheckCircle2 className="text-emerald-500" size={18} />
            <p className="mt-3 text-sm font-semibold">Completed</p>
            <p className="mt-1 text-xs text-slate-500">
              Execution results are posted back to the server.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
