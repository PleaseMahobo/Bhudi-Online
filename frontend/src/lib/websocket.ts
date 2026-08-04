import { useEffect, useRef, useState } from "react";

const WS_URL =
  (
    process.env.NEXT_PUBLIC_API_URL ??
    "https://bhudi-online-production.up.railway.app"
  )
    .replace(/^http/, "ws") + "/ws";

export function createSocket(
  deviceId: string | number,
  onMessage: (data: any) => void
) {
  const socket = new WebSocket(`${WS_URL}?device=${deviceId}`);

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

  const [messages, setMessages] = useState<any[]>([]);
  const [isConnected, setConnected] = useState(false);

  useEffect(() => {
    const socket = createSocket(deviceId ?? "", (message) => {
      setMessages((prev) => [message, ...prev].slice(0, 50));
    });

    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);

    return () => socket.close();
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