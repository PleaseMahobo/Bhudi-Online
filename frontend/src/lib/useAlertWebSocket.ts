'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface LiveAlert { id: string; check_id?: string | null; provider?: string; alert_type?: string; severity: string; message?: string; fingerprint?: string | null; correlation_key?: string | null; correlated_count?: number; suppressed?: boolean; suppression_reason?: string | null; maintenance_window?: string | null; escalation_level?: number; anomaly_score?: number | null; state_transition?: string | null; context?: Record<string, any> | null; resolved?: boolean; status?: string; created_at?: string | null; }
export interface AlertSocketEvent { type: string; channel?: string; alert?: LiveAlert; data?: { id: string; tenant_id?: string; status?: string; resolved?: boolean }; message?: string; count?: number; events?: AlertSocketEvent[]; }

function buildWsUrl(): string { const base = process.env.NEXT_PUBLIC_API_URL ?? 'https://bhudi-online-production.up.railway.app'; return base.replace(/^http/, 'ws') + '/ws/alerts'; }

function applyEvent(data: AlertSocketEvent, setAlerts: React.Dispatch<React.SetStateAction<LiveAlert[]>>) {
  if (data.type === 'alert.created' && data.alert) setAlerts(prev => prev.some(a => a.id === data.alert!.id) ? prev : [data.alert!, ...prev].slice(0, 100));
  if (data.type === 'alert.updated' && data.data) setAlerts(prev => prev.map(a => a.id === data.data!.id ? { ...a, status: data.data!.status, resolved: data.data!.resolved } : a));
  if (data.type === 'alert.resolved' && data.alert) setAlerts(prev => prev.map(a => a.id === data.alert!.id ? { ...a, resolved: true, status: 'resolved' } : a));
}

export function useAlertWebSocket(enabled = true) {
  const socketRef = useRef<WebSocket | null>(null); const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null); const [alerts, setAlerts] = useState<LiveAlert[]>([]); const [isConnected, setConnected] = useState(false); const [lastEvent, setLastEvent] = useState<AlertSocketEvent | null>(null);
  const handleMessage = useCallback((raw: MessageEvent) => { try { const data: AlertSocketEvent = JSON.parse(raw.data); setLastEvent(data); if (data.type === 'batch' && Array.isArray(data.events)) { [...data.events].reverse().forEach(event => applyEvent(event, setAlerts)); return; } applyEvent(data, setAlerts); } catch {} }, []);
  const connect = useCallback(() => { if (!enabled || typeof window === 'undefined') return; if (socketRef.current && [WebSocket.OPEN, WebSocket.CONNECTING].includes(socketRef.current.readyState)) return; const ws = new WebSocket(buildWsUrl()); socketRef.current = ws; ws.onopen = () => setConnected(true); ws.onmessage = handleMessage; ws.onclose = () => { setConnected(false); socketRef.current = null; reconnectTimer.current = setTimeout(connect, 3000); }; ws.onerror = () => ws.close(); }, [enabled, handleMessage]);
  useEffect(() => { connect(); return () => { if (reconnectTimer.current) clearTimeout(reconnectTimer.current); socketRef.current?.close(); socketRef.current = null; }; }, [connect]);
  return { alerts, isConnected, lastEvent, clearAlerts: () => setAlerts([]) };
}
