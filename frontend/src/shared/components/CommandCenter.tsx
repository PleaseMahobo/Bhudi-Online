'use client';

import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Clock3, Command, Loader2, Play, Terminal, XCircle } from 'lucide-react';
import { getDevices } from '@/lib/api';

type Device = { id: string; hostname?: string; name?: string; status?: string };
type CommandDefinition = { type: string; name: string; description: string; read_only: boolean; requires_confirmation?: boolean };
type Result = { exit_code: number; stdout: string; stderr: string; metadata?: Record<string, unknown> };

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';
const token = () => typeof window === 'undefined' ? '' : localStorage.getItem('access_token') || '';

export default function CommandCenter() {
  const [commands, setCommands] = useState<CommandDefinition[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [commandType, setCommandType] = useState('inventory');
  const [deviceId, setDeviceId] = useState('');
  const [script, setScript] = useState('');
  const [interpreter, setInterpreter] = useState('powershell');
  const [output, setOutput] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    void Promise.all([
      fetch(`${API_BASE}/api/v1/command-catalog`, { headers: { Authorization: `Bearer ${token()}` } }).then((r) => r.json()).catch(() => ({ commands: [] })),
      getDevices().catch(() => []),
    ]).then(([catalog, deviceRows]) => {
      setCommands(Array.isArray(catalog.commands) ? catalog.commands : []);
      setDevices(Array.isArray(deviceRows) ? deviceRows as Device[] : []);
    });
  }, []);

  const selected = useMemo(() => commands.find((c) => c.type === commandType), [commands, commandType]);

  async function execute() {
    if (!deviceId) return setError('Select a target device.');
    if (selected?.requires_confirmation && !window.confirm(`Run ${selected.name} on the selected device?`)) return;
    setBusy(true); setError(''); setOutput(null);
    try {
      const payload: Record<string, unknown> = { device_id: deviceId, command_type: commandType };
      if (commandType === 'remote_script') { payload.script = script; payload.interpreter = interpreter; }
      if (commandType === 'remote_powershell') payload.command = script;
      const response = await fetch(`${API_BASE}/api/v1/commands/execute`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Command execution failed');
      setOutput(data.result || data);
    } catch (e) { setError(e instanceof Error ? e.message : 'Command execution failed'); }
    finally { setBusy(false); }
  }

  return <div className="space-y-6">
    <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
      <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-sm font-semibold"><Command size={17} className="text-indigo-600" /> Command library</div><div className="mt-4 space-y-1">{commands.map((command) => <button key={command.type} type="button" onClick={() => { setCommandType(command.type); setOutput(null); setError(''); }} className={`w-full rounded-lg px-3 py-2 text-left text-sm ${command.type === commandType ? 'bg-indigo-50 font-semibold text-indigo-700' : 'text-slate-600 hover:bg-slate-50'}`}>{command.name}</button>)}</div></aside>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between gap-4"><div><p className="text-lg font-semibold text-slate-900">{selected?.name || commandType}</p><p className="mt-1 text-sm text-slate-500">{selected?.description}</p></div>{selected?.read_only ? <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">Read only</span> : <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">Action</span>}</div>
        <div className="mt-6 grid gap-4 md:grid-cols-2"><label className="block text-sm font-medium text-slate-700">Target device<select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"><option value="">Select device</option>{devices.map((d) => <option key={d.id} value={d.id}>{d.hostname || d.name || d.id} · {d.status || 'unknown'}</option>)}</select></label>{commandType === 'remote_script' && <label className="block text-sm font-medium text-slate-700">Interpreter<select value={interpreter} onChange={(e) => setInterpreter(e.target.value)} className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"><option value="powershell">PowerShell</option><option value="bash">Bash</option><option value="sh">SH</option><option value="python">Python</option></select></label>}</div>
        {(commandType === 'remote_script' || commandType === 'remote_powershell') && <label className="mt-4 block text-sm font-medium text-slate-700">{commandType === 'remote_powershell' ? 'PowerShell command' : 'Script'}<textarea value={script} onChange={(e) => setScript(e.target.value)} rows={9} className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-950 p-4 font-mono text-sm text-slate-100 outline-none focus:ring-2 focus:ring-indigo-200" placeholder={commandType === 'remote_powershell' ? 'Get-Service | Where-Object Status -eq Running' : '# enter your script'} /></label>}
        {error && <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"><XCircle size={16} />{error}</div>}
        <button type="button" onClick={execute} disabled={busy || !deviceId} className="mt-5 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50">{busy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}{busy ? 'Executing…' : `Run ${selected?.name || 'Command'}`}</button>
      </section>
    </div>
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm"><header className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-sm font-semibold"><Terminal size={17} className="text-indigo-600" /> Execution result</header>{output ? <div className="p-5"><div className="flex items-center gap-2 text-sm">{output.exit_code === 0 ? <CheckCircle2 className="text-emerald-500" size={17} /> : <XCircle className="text-red-500" size={17} />} Exit code: <b>{output.exit_code}</b></div><pre className="mt-4 max-h-[420px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-200">{output.stdout || output.stderr || 'Command completed without output.'}</pre></div> : <div className="px-5 py-10 text-center text-sm text-slate-500"><Clock3 className="mx-auto mb-2 text-slate-300" size={22} />Run a command to see its structured output here.</div>}</section>
  </div>;
}
