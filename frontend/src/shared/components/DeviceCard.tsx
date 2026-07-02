"use client";

import { useEffect, useState } from "react";
import CommandPanel from "./CommandPanel";

function createSocket(deviceId: string, onMessage: (data: any) => void) {
  if (typeof window === "undefined") {
    return { close: () => {} };
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/${deviceId}`);

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      // ignore invalid websocket messages
    }
  };

  socket.onclose = () => {
    onMessage({ type: "offline" });
  };

  return socket;
}

export default function DeviceCard({ device }: any) {
  const [status, setStatus] = useState(device.status);

  useEffect(() => {
    const ws = createSocket(device.id, (data) => {
      if (data.type === "heartbeat") {
        setStatus("online");
      }
      if (data.type === "offline") {
        setStatus("offline");
      }
    });

    return () => ws.close();
  }, []);

  return (
    <div className="border rounded-lg p-4 shadow">
      <h2 className="font-bold">{device.hostname}</h2>
      <p>IP: {device.ip_address}</p>

      <span
        className={
          status === "online"
            ? "text-green-500"
            : "text-red-500"
        }
      >
        {status}
      </span>

      <CommandPanel deviceId={device.id} />
    </div>
  );
}