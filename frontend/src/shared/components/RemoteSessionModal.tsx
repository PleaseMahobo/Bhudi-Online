'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader2, ScreenShare, X } from 'lucide-react';

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
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

export default function RemoteSessionModal({
  agentId,
  hostname,
  onClose,
}: {
  agentId: string;
  hostname?: string;
  onClose: () => void;
}) {
  const [status, setStatus] = useState('Starting…');
  const [error, setError] = useState('');
  const [frameUrl, setFrameUrl] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(API_BASE + '/api/v1/runtime/remote/desktop', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({
            agent_id: agentId,
            session_mode: 'control',
            display_protocol: 'native',
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || res.statusText);
        const sid = data.session_id as string;
        if (!sid) throw new Error('No session_id');
        if (cancelled) return;
        setStatus('Connected — waiting for frames');
        const ws = new WebSocket(
          wsBase() + '/api/v1/remote-access/sessions/' + sid + '/dashboard'
        );
        wsRef.current = ws;
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(String(ev.data));
            if (msg.type === 'desktop_ready') setStatus('Desktop ready — streaming');
            if (msg.type === 'frame' && msg.data) {
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
            if (msg.type === 'session_closed') setStatus('Session ended');
          } catch {
            /* ignore */
          }
        };
        ws.onerror = () => setError('WebSocket error');
        ws.onclose = () => setStatus((s) => (s.includes('ended') ? s : 'Disconnected'));
      } catch (e: any) {
        setError(e?.message || 'Failed to start remote session');
        setStatus('Failed');
      }
    })();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [agentId]);

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/50 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <ScreenShare size={16} className="text-indigo-600" />
            Remote — {hostname || agentId.slice(0, 8)}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500">{status}</span>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"
            >
              <X size={18} />
            </button>
          </div>
        </header>
        {error && (
          <div className="border-b border-red-100 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
        )}
        <div className="relative flex min-h-[360px] flex-1 items-center justify-center overflow-auto bg-slate-950">
          <canvas ref={canvasRef} className="max-h-full max-w-full" />
          {!frameUrl && !error && (
            <div className="absolute flex items-center gap-2 text-sm text-slate-400">
              <Loader2 className="animate-spin" size={16} />
              Waiting for frames (agent must be online on an interactive desktop)…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
