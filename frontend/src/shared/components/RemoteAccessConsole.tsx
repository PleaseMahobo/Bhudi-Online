'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, Monitor, RefreshCw, Terminal, Wifi, XCircle } from 'lucide-react';
import { getDevices } from '@/lib/api';

type Device = { id: string; device_id?: string; agent_id?: string; hostname?: string; name?: string; status?: string };
type MonitorInfo = { index: number; name: string; width: number; height: number; primary?: boolean };
// HTTP stays same-origin so Next.js auth proxies can attach cookies.
const API_BASE = '';

// WebSockets must hit the Railway API host (Vercel cannot upgrade / proxy WS to FastAPI).
function apiHttpBase(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app').trim();
  return raw.replace(/\/$/, '');
}

function wsBase(): string {
  return apiHttpBase().replace(/^http/, 'ws');
}

function authHeaders(): HeadersInit {
  return { 'Content-Type': 'application/json', Accept: 'application/json' };
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
  const [termInput, setTermInput] = useState('');
  const [hasFrame, setHasFrame] = useState(false);
  const [monitors, setMonitors] = useState<MonitorInfo[]>([]);
  const [monitorIndex, setMonitorIndex] = useState(0);
  const [fitMode, setFitMode] = useState<'contain' | 'width'>('contain');
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

  useEffect(() => () => {
    wsRef.current?.close();
  }, []);

  function deviceAgentId(d: Device): string {
    return String(d.agent_id || d.device_id || d.id || '');
  }

  function sendInput(payload: Record<string, unknown>) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(payload));
  }

  function drawFrame(b64: string, w?: number, h?: number) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const img = new Image();
    img.onload = () => {
      const width = w || img.width || frameSize.current.w;
      const height = h || img.height || frameSize.current.h;
      frameSize.current = { w: width, h: height };
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(img, 0, 0, width, height);
      setHasFrame(true);
    };
    img.src = b64.startsWith('data:') ? b64 : `data:image/jpeg;base64,${b64}`;
  }

  async function startSession() {
    if (!agentId) {
      setError('Select a device / agent first.');
      return;
    }
    setBusy(true);
    setError('');
    setStatus('Queueing session…');
    setHasFrame(false);
    setTermLog('');
    wsRef.current?.close();

    try {
      const path =
        mode === 'desktop'
          ? '/api/v1/runtime/remote/desktop'
          : '/api/v1/runtime/remote/terminal';
      const body =
        mode === 'desktop'
          ? {
              agent_id: agentId,
              session_mode: 'control',
              display_protocol: 'native',
              monitor_index: monitorIndex,
            }
          : { agent_id: agentId, shell };

      const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: authHeaders(),
        credentials: 'include',
        cache: 'no-store',
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          (typeof data.detail === 'string' && data.detail) ||
            res.statusText ||
            'Failed to start'
        );
      }
      const sid = data.session_id as string;
      if (!sid) throw new Error('No session_id returned');
      setSessionId(sid);
      setStatus('Connecting…');

      const url = `${wsBase()}/api/v1/remote-access/sessions/${sid}/dashboard`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setStatus('Connected — waiting for agent');
      ws.onerror = () =>
        setError(
          `WebSocket error — check NEXT_PUBLIC_API_URL and agent online (stream: ${url})`
        );
      ws.onclose = () => setStatus('Disconnected');
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data));
          const type = msg.type as string;
          if (type === 'desktop_ready') {
            setStatus('Desktop ready');
            if (Array.isArray(msg.monitors)) setMonitors(msg.monitors);
          } else if (type === 'frame' || type === 'desktop_frame') {
            const b64 = msg.data || msg.frame || msg.image;
            if (typeof b64 === 'string') drawFrame(b64, msg.width, msg.height);
          } else if (type === 'terminal_output' || type === 'stdout') {
            const chunk = String(msg.data || msg.output || msg.text || '');
            if (chunk) setTermLog((prev) => (prev + chunk).slice(-20000));
          } else if (type === 'error') {
            setError(String(msg.message || msg.error || 'Remote session error'));
          } else if (type === 'status') {
            setStatus(String(msg.message || msg.status || 'Active'));
          }
        } catch {
          /* ignore non-JSON */
        }
      };
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start session');
      setStatus('Failed');
    } finally {
      setBusy(false);
    }
  }

  function stopSession() {
    wsRef.current?.close();
    wsRef.current = null;
    setSessionId(null);
    setStatus('Disconnected');
    setHasFrame(false);
  }

  function sendTerm() {
    const cmd = termInput.trim();
    if (!cmd) return;
    sendInput({ type: 'terminal_input', data: cmd + '\n' });
    setTermLog((prev) => prev + `\n> ${cmd}\n`);
    setTermInput('');
  }

  function canvasCoords(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = frameSize.current.w / rect.width;
    const scaleY = frameSize.current.h / rect.height;
    return {
      x: Math.round((e.clientX - rect.left) * scaleX),
      y: Math.round((e.clientY - rect.top) * scaleY),
    };
  }

  function onCanvasMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    const { x, y } = canvasCoords(e);
    sendInput({ type: 'mouse', action: 'down', button: e.button, x, y });
  }
  function onCanvasMouseUp(e: React.MouseEvent<HTMLCanvasElement>) {
    const { x, y } = canvasCoords(e);
    sendInput({ type: 'mouse', action: 'up', button: e.button, x, y });
  }
  function onCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    const { x, y } = canvasCoords(e);
    sendInput({ type: 'mouse', action: 'click', button: e.button, x, y });
  }
  function onCanvasMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const { x, y } = canvasCoords(e);
    sendInput({ type: 'mouse', action: 'move', x, y });
  }
  function onCanvasWheel(e: React.WheelEvent<HTMLCanvasElement>) {
    e.preventDefault();
    const { x, y } = canvasCoords(e);
    sendInput({ type: 'mouse', action: 'wheel', x, y, deltaY: e.deltaY });
  }
  function onCanvasKeyDown(e: React.KeyboardEvent<HTMLCanvasElement>) {
    e.preventDefault();
    sendInput({ type: 'key', action: 'down', key: e.key, code: e.code });
  }
  function onCanvasKeyUp(e: React.KeyboardEvent<HTMLCanvasElement>) {
    e.preventDefault();
    sendInput({ type: 'key', action: 'up', key: e.key, code: e.code });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="min-w-[220px] flex-1">
          <label className="mb-1 block text-xs font-medium text-slate-500">Device / agent</label>
          <select
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="">Select device…</option>
            {devices.map((d) => {
              const id = deviceAgentId(d);
              const label = d.hostname || d.name || id;
              return (
                <option key={id} value={id}>
                  {label} ({d.status || 'unknown'})
                </option>
              );
            })}
          </select>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setMode('desktop')}
            className={
              'inline-flex items-center gap-1 rounded-xl px-3 py-2 text-sm font-medium ' +
              (mode === 'desktop' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700')
            }
          >
            <Monitor className="h-4 w-4" /> Desktop
          </button>
          <button
            type="button"
            onClick={() => setMode('terminal')}
            className={
              'inline-flex items-center gap-1 rounded-xl px-3 py-2 text-sm font-medium ' +
              (mode === 'terminal' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700')
            }
          >
            <Terminal className="h-4 w-4" /> Terminal
          </button>
        </div>

        {mode === 'desktop' && (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Display</label>
            <select
              value={monitorIndex}
              onChange={(e) => setMonitorIndex(Number(e.target.value))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              {monitors.length === 0 ? (
                <option value={0}>Primary / Display 1</option>
              ) : (
                monitors.map((m) => (
                  <option key={m.index} value={m.index}>
                    {m.name || `Display ${m.index + 1}`}
                    {m.primary ? ' ★' : ''}
                  </option>
                ))
              )}
            </select>
          </div>
        )}

        {mode === 'terminal' && (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Shell</label>
            <select
              value={shell}
              onChange={(e) => setShell(e.target.value)}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="powershell">PowerShell</option>
              <option value="cmd">CMD</option>
              <option value="bash">bash</option>
            </select>
          </div>
        )}

        <div className="flex gap-2">
          {!sessionId ? (
            <button
              type="button"
              onClick={() => void startSession()}
              disabled={busy || !agentId}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wifi className="h-4 w-4" />}
              Connect
            </button>
          ) : (
            <button
              type="button"
              onClick={stopSession}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Disconnect
            </button>
          )}
          <button
            type="button"
            onClick={() => void loadDevices()}
            className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="inline-flex items-center gap-1.5 text-slate-600">
          <Wifi className="h-4 w-4" />
          Status: <strong>{status}</strong>
          {sessionId ? (
            <span className="font-mono text-xs text-slate-400">session {sessionId.slice(0, 8)}…</span>
          ) : null}
        </span>
        {error ? (
          <span className="inline-flex items-center gap-1 text-red-600">
            <XCircle className="h-4 w-4" /> {error}
          </span>
        ) : null}
      </div>

      {mode === 'desktop' && (
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-sm">
          <div className="flex items-center justify-between border-b border-white/10 px-3 py-2 text-xs text-slate-300">
            <span>Remote desktop</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setFitMode('contain')}
                className={'rounded px-2 py-1 ' + (fitMode === 'contain' ? 'bg-white/15 text-white' : 'hover:bg-white/10')}
              >
                Fit page
              </button>
              <button
                type="button"
                onClick={() => setFitMode('width')}
                className={'rounded px-2 py-1 ' + (fitMode === 'width' ? 'bg-white/15 text-white' : 'hover:bg-white/10')}
              >
                Fit width
              </button>
              <button
                type="button"
                onClick={() => {
                  const el = canvasRef.current?.parentElement;
                  if (el?.requestFullscreen) void el.requestFullscreen();
                }}
                className="rounded px-2 py-1 hover:bg-white/10"
              >
                Fullscreen
              </button>
            </div>
          </div>
          <div
            className={
              'relative flex bg-black p-2 ' +
              (fitMode === 'contain'
                ? 'max-h-[min(80vh,900px)] items-center justify-center overflow-auto'
                : 'items-start justify-center overflow-auto')
            }
          >
            <canvas
              ref={canvasRef}
              tabIndex={0}
              onMouseDown={onCanvasMouseDown}
              onMouseUp={onCanvasMouseUp}
              onClick={onCanvasClick}
              onMouseMove={onCanvasMouseMove}
              onWheel={onCanvasWheel}
              onKeyDown={onCanvasKeyDown}
              onKeyUp={onCanvasKeyUp}
              onContextMenu={(e) => e.preventDefault()}
              style={{
                display: 'block',
                width: fitMode === 'width' ? '100%' : 'auto',
                maxWidth: '100%',
                maxHeight: fitMode === 'contain' ? 'min(80vh, 880px)' : undefined,
                height: 'auto',
                cursor: 'crosshair',
              }}
              className="outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {!hasFrame && (
              <p className="pointer-events-none absolute text-sm text-slate-500">
                No frames yet — Connect with agent v2.2.8+.
              </p>
            )}
          </div>
          <p className="border-t border-white/10 px-3 py-1.5 text-[11px] text-slate-500">
            Click the screen to focus, then click/drag/type. Change Display and reconnect to switch monitors.
          </p>
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
