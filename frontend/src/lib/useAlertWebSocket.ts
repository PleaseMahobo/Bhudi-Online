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
  const base =
    process.env.NEXT_PUBLIC_API_URL ??
    'https://bhudi-online-production.up.railway.app';
  return base.replace(/^http/, 'ws') + '/ws/alerts';
}

function applyEvent(
  data: AlertSocketEvent,
  setAlerts: React.Dispatch<React.SetStateAction<LiveAlert[]>>
) {
  if (data.type === 'alert.created' && data.alert) {
    setAlerts((prev) => {
      // De-dupe by id if the same alert arrives twice
      if (prev.some((a) => a.id === data.alert!.id)) return prev;
      return [data.alert!, ...prev].slice(0, 100);
    });
  }

  if (data.type === 'alert.resolved' && data.alert) {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === data.alert!.id ? { ...a, resolved: true } : a
      )
    );
  }
}

export function useAlertWebSocket(enabled = true) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [alerts, setAlerts] = useState<LiveAlert[]>([]);
  const [isConnected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<AlertSocketEvent | null>(null);

  const handleMessage = useCallback((raw: MessageEvent) => {
    try {
      const data: AlertSocketEvent = JSON.parse(raw.data);
      setLastEvent(data);

      // Batched envelope from the server
      if (data.type === 'batch' && Array.isArray(data.events)) {
        // Process oldest → newest so list order stays correct
        const ordered = [...data.events].reverse();
        for (const event of ordered) {
          applyEvent(event, setAlerts);
        }
        return;
      }

      // Single event (immediate send or batch of size 1)
      applyEvent(data, setAlerts);
    } catch {
      // ignore malformed payloads
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled || typeof window === 'undefined') return;

    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const ws = new WebSocket(buildWsUrl());
    socketRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = handleMessage;

    ws.onclose = () => {
      setConnected(false);
      socketRef.current = null;
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [enabled, handleMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [connect]);

  const clearAlerts = () => setAlerts([]);

  return {
    alerts,
    isConnected,
    lastEvent,
    clearAlerts,
  };
}
