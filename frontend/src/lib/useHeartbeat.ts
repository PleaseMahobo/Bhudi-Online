// frontend/src/lib/useHeartbeat.ts
import { useEffect, useRef } from 'react';

export function useHeartbeat(deviceId: string = "main-agent") {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${process.env.NEXT_PUBLIC_API_URL?.replace('https://', '').replace('http://', '')}/ws`;

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected - Heartbeat active");
      // Send initial heartbeat
      socket.send(JSON.stringify({
        type: "heartbeat",
        device_id: deviceId,
        timestamp: Date.now(),
        status: "online"
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("Heartbeat update:", data);
    };

    // Send heartbeat every 10 seconds
    const interval = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: "heartbeat",
          device_id: deviceId,
          timestamp: Date.now(),
          status: "online"
        }));
      }
    }, 10000);

    return () => {
      clearInterval(interval);
      socket.close();
    };
  }, [deviceId]);

  return socketRef;
}