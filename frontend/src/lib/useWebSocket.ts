// frontend/src/lib/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace('https://', '').replace('http://', '') || 'localhost:8000';
    const wsUrl = `${protocol}//${baseUrl}/ws`;

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      console.log("✅ WebSocket Connected with Heartbeat");
    };

    socket.onmessage = (event) => {
      try {
        if (typeof event.data === 'string' && event.data.trim()) {
          const data = JSON.parse(event.data);
          console.log("Live WebSocket update:", data);
        }
      } catch (e) {
        // Silently ignore non-JSON messages (common during handshake)
        console.debug("Non-JSON WebSocket message received");
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      console.log("❌ WebSocket Disconnected");

      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++;
        reconnectTimeoutRef.current = setTimeout(connect, 2000);
      }
    };

    socket.onerror = () => {
      console.error("WebSocket error");
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { isConnected, sendMessage };
}