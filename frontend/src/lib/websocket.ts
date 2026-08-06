import { useEffect, useRef, useState } from "react";

const WS_BASE =
  (
    process.env.NEXT_PUBLIC_API_URL ??
    "https://bhudi-online-production.up.railway.app"
  ).replace(/^http/, "ws");

export function createSocket(
  deviceId: string | number,
  onMessage: (data: any) => void
) {
  const url = deviceId
    ? `${WS_BASE}/ws/${deviceId}`
    : `${WS_BASE}/ws`;
  const socket = new WebSocket(url);

  socket.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch {
      onMessage(event.data);
    }
  };

  return socket;
}

export function useWebSocket(deviceId?: string | number) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [messages, setMessages] = useState<any[]>([]);
  const [isConnected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;

      const socket = createSocket(deviceId ?? "", (message) => {
        setMessages((prev) => [message, ...prev].slice(0, 50));
      });

      socketRef.current = socket;

      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        if (!cancelled) {
          reconnectTimer.current = setTimeout(connect, 3000);
        }
      };
      socket.onerror = () => socket.close();
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
    };
  }, [deviceId]);

  const sendMessage = (message: unknown) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  };

  return {
    messages,
    isConnected,
    sendMessage,
  };
}
