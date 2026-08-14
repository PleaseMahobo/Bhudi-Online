'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader2, ScreenShare, X } from 'lucide-react';

function apiHttpBase(): string {
  let raw = (process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app').trim();
  raw = raw.split(/\s+/)[0] || raw;
  raw = raw.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
  if (!/^https?:\/\//i.test(raw)) raw = 'https://' + raw;
  return raw;
}

const API_BASE = apiHttpBase();

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') || '' : '';
  return token
    ? { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

function wsBase(): string {
  const http = API_BASE;
  if (http.startsWith('https://')) return 'wss://' + http.slice('https://'.length);
  if (http.startsWith('http://')) return 'ws://' + http.slice('http://'.length);
  return 'wss://' + http;
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
        ws.onerror = () => setError('WebSocket error — agent must be online and enrolled');
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3">
          <div className="flex items-center gap-2 text-sm text-white">
            <ScreenShare size={16} className="text-indigo-400" />
            Remote — {hostname || agentId}
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={18} />
          </button>
        </div>
        <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-2 text-xs text-slate-400">
          {status === 'Starting…' || status.includes('waiting') ? <Loader2 size={12} className="animate-spin" /> : null}
          {status}
          {error ? <span className="text-red-400">{error}</span> : null}
        </div>
        <div className="relative min-h-[320px] flex-1 bg-black">
          <canvas ref={canvasRef} className="mx-auto max-h-[70vh] max-w-full" />
          {!frameUrl && !error && (
            <p className="absolute inset-0 flex items-center justify-center text-sm text-slate-500">
              Waiting for desktop frames…
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
