// frontend/lib/useWebSocket.ts
// Allow usage of `process` in browser/TS without @types/node
declare const process: { env: { [key: string]: string | undefined } };
// @ts-ignore: `react` types are not available in this workspace
import { useEffect, useRef, useState } from 'react';

export function useWebSocket() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = `wss://${process.env.NEXT_PUBLIC_API_URL?.replace('https://', '')}/ws`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => setIsConnected(true);
    socket.onclose = () => setIsConnected(false);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev: any) => [data, ...prev].slice(0, 50)); // Keep last 50 messages
    };

    return () => socket.close();
  }, []);

  const sendMessage = (message: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  };

  return { messages, isConnected, sendMessage };
}