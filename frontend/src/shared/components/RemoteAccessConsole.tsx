'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Loader2,
  Monitor,
  RefreshCw,
  ScreenShare,
  Terminal,
  Wifi,
  XCircle,
} from 'lucide-react';
import { getDevices } from '@/lib/api';

type Device = {
  id: string;
  device_id?: string;
  agent_id?: string;
  hostname?: string;
  name?: string;
  status?: string;
};

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

function authHeaders(): HeadersInit {
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

function wsBase(): string {
  try {
    const u = new URL(API_BASE);
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return u.origin;
  } catch {
    return API_BASE.replace(/^http/, 'ws');
  }
}

export default function RemoteAccessConsole() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [agentId, setAgentId] = useState('');
  const [mode, setMode] = useState<'desktop' | 'terminal'>('desktop');
  const [shell, setShell] = useState('powershell');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState('Idle');
  const [termLog, setTermLog] = useState('');
  const [frameUrl, setFrameUrl] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameSize = useRef({ w: 1280, h: 720 });

  const loadDevices = useCallback(async () => {
    try {
      const rows = await getDevices().catch(() => []);
      setDevices(Array.isArray(rows) ? (rows as Device[]) : []);
    } catch {
      setDevices([]);
    }
  }, []);

  useEffect(() => {
    void loadDevices();
    const id = setInterval(loadDevices, 15000);
    return () => clearInterval(id);
  }, [loadDevices]);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  function deviceAgentId(d: Device): string {
    return String(d.agent_id || d.device_id || d.id || '');
  }

  async function startSession() {
    if (!agentId) {
      setError('Select a device / agent first.');
      return;
    }
    setBusy(true);
    setError('');
    setTermLog('');
    setFrameUrl(null);
    setStatus('Queueing session…');
    wsRef.current?.close();

    try {
      const path =
        mode === 'desktop'
          ? '/api/v1/runtime/remote/desktop'
          : '/api/v1/runtime/remote/terminal';
      const body =
        mode === 'desktop'
          ? { agent_id: agentId, session_mode: 'control', display_protocol: 'native' }
          : { agent_id: agentId, shell, interactive: true };

      const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || data.message || `HTTP ${res.status}`;
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }

      const sid = data.session_id as string;
      if (!sid) throw new Error('No session_id returned');
      setSessionId(sid);
      setStatus('Waiting for agent… (agent must be online, v2.2+)');

      const url = `${wsBase()}/api/v1/remote-access/sessions/${sid}/dashboard`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setStatus('Dashboard connected — waiting for agent…');
      ws.onerror = () => setError('WebSocket error — check backend URL.');
      ws.onclose = () => setStatus((s) => (s.includes('ended') ? s : 'Session closed'));
      ws.onmessage = (ev) => {
        let msg: Record<string, unknown>;
        try {
          msg = JSON.parse(String(ev.data));
        } catch {
          return;
        }
        const type = String(msg.type || '');

        if (type === 'agent_connected') setStatus('Agent connected');
        if (type === 'agent_disconnected') setStatus('Agent disconnected');
        if (type === 'desktop_ready') {
          setStatus('Desktop ready');
          if (msg.width && msg.height) {
            frameSize.current = { w: Number(msg.width), h: Number(msg.height) };
          }
        }
        if (type === 'terminal_ready') {
          setStatus('Terminal ready');
          setTermLog(
            (l) =>
              l +
              `\n[ready] shell=${msg.shell || ''} platform=${msg.platform || ''}\n`
          );
        }
        if (type === 'frame' && msg.data) {
          setStatus('Streaming');
          const encoding = String(msg.encoding || 'jpeg');
          const dataUrl = `data:image/${encoding};base64,${msg.data}`;
          setFrameUrl(dataUrl);
          const img = new Image();
          img.onload = () => {
            const canvas = canvasRef.current;
            if (!canvas) return;
            const w = Number(msg.width) || img.width;
            const h = Number(msg.height) || img.height;
            frameSize.current = { w, h };
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx?.drawImage(img, 0, 0, w, h);
          };
          img.src = dataUrl;
        }
        if (type === 'output' && msg.data) {
          setTermLog((l) => l + String(msg.data));
        }
        if (type === 'error') {
          setError(String(msg.message || 'Session error'));
        }
        if (type === 'session_closed') setStatus('Session ended');
      };
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start session');
      setStatus('Failed');
    } finally {
      setBusy(false);
    }
  }

  function sendInput(payload: Record<string, unknown>) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(payload));
  }

  function onCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / rect.width) * frameSize.current.w);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * frameSize.current.h);
    sendInput({ type: 'click', x, y, button: e.button === 2 ? 'right' : 'left' });
  }

  function onTermKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const line = (e.target as HTMLTextAreaElement).value;
      const parts = line.split('\n');
      const cmd = parts[parts.length - 1] || '';
      sendInput({ type: 'command', command: cmd });
    }
  }

  function stopSession() {
    sendInput({ type: 'close' });
    wsRef.current?.close();
    setSessionId(null);
    setStatus('Stopped');
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Remote Access</h1>
          <p className="mt-1 text-sm text-slate-500">
            Screen share and interactive terminal for online native agents (v2.2+).
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadDevices()}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={15} />
          Refresh devices
        </button>
      </div>

      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">
            Target device
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"
            >
              <option value="">Select online agent…</option>
              {devices.map((d) => {
                const id = deviceAgentId(d);
                return (
                  <option key={id} value={id}>
                    {(d.hostname || d.name || id) + ' · ' + (d.status || 'unknown')}
                  </option>
                );
              })}
            </select>
          </label>

          <div>
            <p className="text-sm font-medium text-slate-700">Session type</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setMode('desktop')}
                className={
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ' +
                  (mode === 'desktop'
                    ? 'border-indigo-300 bg-indigo-50 text-indigo-800'
                    : 'border-slate-200 text-slate-600')
                }
              >
                <ScreenShare size={14} /> Screen share
              </button>
              <button
                type="button"
                onClick={() => setMode('terminal')}
                className={
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ' +
                  (mode === 'terminal'
                    ? 'border-indigo-300 bg-indigo-50 text-indigo-800'
                    : 'border-slate-200 text-slate-600')
                }
              >
                <Terminal size={14} /> Terminal
              </button>
            </div>
            {mode === 'terminal' && (
              <select
                value={shell}
                onChange={(e) => setShell(e.target.value)}
                className="mt-2 h-9 rounded-lg border border-slate-200 px-2 text-sm"
              >
                <option value="powershell">PowerShell</option>
                <option value="cmd">CMD</option>
                <option value="bash">Bash</option>
                <option value="zsh">Zsh</option>
              </select>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || !agentId}
            onClick={() => void startSession()}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Monitor size={16} />}
            {busy ? 'Starting…' : 'Connect'}
          </button>
          {sessionId && (
            <button
              type="button"
              onClick={stopSession}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700"
            >
              Disconnect
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Wifi size={14} />
          Status: <span className="font-medium text-slate-800">{status}</span>
          {sessionId && (
            <span className="font-mono text-slate-400">session {sessionId.slice(0, 8)}…</span>
          )}
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            <XCircle size={16} className="mt-0.5 shrink-0" />
            <div>
              <p>{error}</p>
              <p className="mt-1 text-xs text-red-600/80">
                Common causes: agent offline, agent older than v2.2, backend restarted (re-enroll agent),
                or agent id mismatch.
              </p>
            </div>
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 shadow-sm">
        <header className="border-b border-slate-800 px-4 py-3 text-sm font-semibold text-slate-200">
          {mode === 'desktop' ? 'Live screen' : 'Live terminal'}
        </header>
        {mode === 'desktop' ? (
          <div className="relative flex min-h-[360px] items-center justify-center bg-black p-2">
            <canvas
              ref={canvasRef}
              onClick={onCanvasClick}
              onContextMenu={(e) => e.preventDefault()}
              className="max-h-[70vh] max-w-full cursor-crosshair"
            />
            {!frameUrl && (
              <p className="absolute text-sm text-slate-500">No frames yet — click Connect</p>
            )}
          </div>
        ) : (
          <div className="p-3">
            <pre className="h-72 overflow-auto whitespace-pre-wrap font-mono text-xs text-emerald-400">
              {termLog || 'Terminal output will appear here after Connect…'}
            </pre>
            <textarea
              rows={2}
              onKeyDown={onTermKey}
              placeholder="Type a command and press Enter"
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-sm text-slate-100"
            />
          </div>
        )}
      </section>
    </div>
  );
}
