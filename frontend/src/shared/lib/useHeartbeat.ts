// frontend/lib/useHeartbeat.ts
import { useEffect, useRef } from 'react';

export function useHeartbeat(deviceId: string = "default-device") {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${process.env.NEXT_PUBLIC_API_URL?.replace('https://', '').replace('http://', '')}/ws`;

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected - Heartbeat started");
      // Send initial heartbeat
      socket.send(JSON.stringify({
        type: "heartbeat",
        device_id: deviceId,
        timestamp: Date.now()
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("Live update:", data);
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

// frontend/lib/useWebSocket.ts
import { useAuth } from "@/shared/auth/AuthContext";
import { User2 } from 'lucide-react';

export function useWebSocket() {
  const { user } = useAuth();
  // ... existing code ...

  useEffect(() => {
    if (!user) return;

    const wsUrl = `wss://${process.env.NEXT_PUBLIC_API_URL?.replace('https://', '')}/ws`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      // Send JWT token for authentication
      const token = (user as any)?.accessToken ?? "demo-token";
      socket.send(JSON.stringify({
        type: "auth",
        token
      }));
    };

    // ... rest of your code
  }, [User2]);
}