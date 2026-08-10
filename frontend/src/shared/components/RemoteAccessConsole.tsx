'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
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
    ? { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
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
  const searchParams = useSearchParams();
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
  const [zoom, setZoom] = useState(100);
  const [wide, setWide] = useState(true);
  const [termInput, setTermInput] = useState('');

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
    const a = searchParams.get('agent') || searchParams.get('device') || '';
    const m = searchParams.get('mode');
    if (a) setAgentId(a);
    if (m === 'desktop' || m === 'terminal') setMode(m);
  }, [searchParams]);

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
    setStatus('Queueing session…');
    setFrameUrl(null);
    setTermLog('');
    try {
      const path =
        mode === 'desktop'
          ? '/api/v1/runtime/remote/desktop'
          : '/api/v1/runtime/remote/terminal';
      const body =
        mode === 'desktop'
          ? { agent_id: agentId, session_mode: 'control', display_protocol: 'native' }
          : { agent_id: agentId, shell };
      const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || 'Failed to start');
      const sid = data.session_id as string;
      if (!sid) throw new Error('No session_id returned');
      setSessionId(sid);
      setStatus('Connecting…');

      const url = wsBase() + '/api/v1/remote-access/sessions/' + sid + '/dashboard';
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => setStatus('Connected — waiting for agent');
      ws.onerror = () => setError('WebSocket error');
      ws.onclose = () => setStatus('Disconnected');
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data));
          const type = msg.type as string;
          if (type === 'desktop_ready') {
            setStatus('Desktop ready');
            if (msg.width && msg.height) frameSize.current = { w: msg.width, h: msg.height };
          }
          if (type === 'frame' && msg.data) {
            const src = 'data:image/jpeg;base64,' + msg.data;
            setFrameUrl(src);
            const img = new Image();
            img.onload = () => {
              const c = canvasRef.current;
              if (!c) return;
              const ctx = c.getContext('2d');
              if (!ctx) return;
              c.width = img.width;
              c.height = img.height;
              ctx.drawImage(img, 0, 0);
            };
            img.src = src;
          }
          if (type === 'terminal_output' || type === 'output') {
            setTermLog((prev) => prev + (msg.data || msg.output || ''));
          }
          if (type === 'session_closed') setStatus('Session ended');
        } catch {
          /* ignore */
        }
      };
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start session');
      setStatus('Idle');
    } finally {
      setBusy(false);
    }
  }

  function stopSession() {
    wsRef.current?.close();
    wsRef.current = null;
    setSessionId(null);
    setStatus('Idle');
    setFrameUrl(null);
  }

  function sendTerm() {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !termInput.trim()) return;
    wsRef.current.send(JSON.stringify({ type: 'input', data: termInput + '\n' }));
    setTermInput('');
  }

  return (
    <div className={'space-y-4 ' + (wide ? '' : 'max-w-5xl')}>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1">
            <label className="mb-1 block text-xs font-medium text-slate-500">Device / agent</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
            >
              <option value="">Select device…</option>
              {devices.map((d) => {
                const id = deviceAgentId(d);
                return (
                  <option key={id} value={id}>
                    {(d.hostname || d.name || id) + (d.status ? ' (' + d.status + ')' : '')}
                  </option>
                );
              })}
            </select>
          </div>
          <div className="flex gap-1 rounded-xl border border-slate-200 p-1">
            <button
              type="button"
              onClick={() => setMode('desktop')}
              className={
                'inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium ' +
                (mode === 'desktop' ? 'bg-indigo-600 text-white' : 'text-slate-600')
              }
            >
              <Monitor size={14} /> Desktop
            </button>
            <button
              type="button"
              onClick={() => setMode('terminal')}
              className={
                'inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium ' +
                (mode === 'terminal' ? 'bg-indigo-600 text-white' : 'text-slate-600')
              }
            >
              <Terminal size={14} /> Terminal
            </button>
          </div>
          {mode === 'terminal' && (
            <select
              value={shell}
              onChange={(e) => setShell(e.target.value)}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="powershell">PowerShell</option>
              <option value="cmd">CMD</option>
              <option value="bash">Bash</option>
            </select>
          )}
          {!sessionId ? (
            <button
              type="button"
              disabled={busy || !agentId}
              onClick={() => void startSession()}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : <ScreenShare size={16} />}
              Connect
            </button>
          ) : (
            <button
              type="button"
              onClick={stopSession}
              className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700"
            >
              <XCircle size={16} /> Disconnect
            </button>
          )}
          <button
            type="button"
            onClick={() => void loadDevices()}
            className="rounded-xl border border-slate-200 p-2 text-slate-600 hover:bg-slate-50"
            title="Refresh devices"
          >
            <RefreshCw size={16} />
          </button>
        </div>
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
          <Wifi size={12} />
          <span>{status}</span>
          {sessionId && <span className="font-mono text-slate-400">session {sessionId.slice(0, 8)}…</span>}
          {agentId && <span className="font-mono text-slate-400">agent {agentId.slice(0, 8)}…</span>}
        </div>
        {error && (
          <div className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
        )}
      </div>

      {mode === 'desktop' && (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between border-b border-white/10 px-3 py-2 text-xs text-slate-300">
            <span>Remote desktop</span>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1">
                Zoom
                <input
                  type="range"
                  min={50}
                  max={150}
                  value={zoom}
                  onChange={(e) => setZoom(Number(e.target.value))}
                />
              </label>
              <button type="button" className="underline" onClick={() => setWide((w) => !w)}>
                {wide ? 'Narrow' : 'Wide'}
              </button>
            </div>
          </div>
          <div className="flex min-h-[360px] items-center justify-center overflow-auto p-2">
            <canvas
              ref={canvasRef}
              style={{ transform: 'scale(' + zoom / 100 + ')', transformOrigin: 'top left' }}
              className="max-w-full bg-black"
            />
            {!frameUrl && (
              <p className="absolute text-sm text-slate-500">No frames yet — start a session with an online agent.</p>
            )}
          </div>
        </div>
      )}

      {mode === 'terminal' && (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 shadow-sm">
          <pre className="max-h-[420px] min-h-[280px] overflow-auto p-4 font-mono text-[12px] text-emerald-300">
            {termLog || 'Terminal output will appear here…'}
          </pre>
          <div className="flex border-t border-white/10">
            <input
              value={termInput}
              onChange={(e) => setTermInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendTerm()}
              placeholder="Type a command…"
              className="flex-1 bg-transparent px-3 py-2 font-mono text-sm text-white outline-none"
              disabled={!sessionId}
            />
            <button
              type="button"
              onClick={sendTerm}
              disabled={!sessionId}
              className="px-4 text-sm font-medium text-indigo-300 hover:text-white disabled:opacity-40"
            >
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
