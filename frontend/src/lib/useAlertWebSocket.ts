'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface LiveAlert {
  id: string;
  check_id?: string | null;
  provider: string;
  alert_type: string;
  severity: string;
  message: string;
  fingerprint?: string | null;
  correlation_key?: string | null;
  correlated_count?: number;
  suppressed?: boolean;
  suppression_reason?: string | null;
  maintenance_window?: string | null;
  escalation_level?: number;
  anomaly_score?: number | null;
  state_transition?: string | null;
  context?: Record<string, any> | null;
  resolved?: boolean;
  created_at?: string | null;
}

export interface AlertSocketEvent {
  type: string;
  channel?: string;
  alert?: LiveAlert;
  message?: string;
  count?: number;
  events?: AlertSocketEvent[];
}

function buildWsUrl(): string {
  let base = (process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app').trim();
  base = base.split(/\s+/)[0] || base;
  base = base.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
  if (!/^https?:\/\//i.test(base)) base = 'https://' + base;
  if (base.startsWith('https://')) return 'wss://' + base.slice('https://'.length) + '/ws/alerts';
  if (base.startsWith('http://')) return 'ws://' + base.slice('http://'.length) + '/ws/alerts';
  return 'wss://' + base + '/ws/alerts';
}

function applyEvent(
  data: AlertSocketEvent,
  setAlerts: React.Dispatch<React.SetStateAction<LiveAlert[]>>
) {
  if (data.type === 'alert.created' && data.alert) {
    setAlerts((prev) => {
      if (prev.some((a) => a.id === data.alert!.id)) return prev;
      return [data.alert!, ...prev].slice(0, 100);
    });
  }
  if (data.type === 'alert.resolved' && data.alert) {
    setAlerts((prev) =>
      prev.map((a) => (a.id === data.alert!.id ? { ...a, resolved: true } : a))
    );
  }
  if (data.type === 'alert.acknowledged' && data.alert) {
    setAlerts((prev) =>
      prev.map((a) => (a.id === data.alert!.id ? { ...a, ...data.alert! } : a))
    );
  }
}

export function useAlertWebSocket(enabled = true) {
  const [alerts, setAlerts] = useState<LiveAlert[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<AlertSocketEvent | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!enabled) return;
    try {
      const ws = new WebSocket(buildWsUrl());
      socketRef.current = ws;
      ws.onopen = () => setIsConnected(true);
      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimer.current = setTimeout(connect, 4000);
      };
      ws.onerror = () => setIsConnected(false);
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(String(ev.data)) as AlertSocketEvent;
          setLastEvent(data);
          applyEvent(data, setAlerts);
          if (Array.isArray(data.events)) {
            data.events.forEach((e) => applyEvent(e, setAlerts));
          }
        } catch {
          /* ignore */
        }
      };
    } catch {
      setIsConnected(false);
    }
  }, [enabled]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [connect]);

  const clearAlerts = () => setAlerts([]);

  return { alerts, isConnected, lastEvent, clearAlerts };
}
