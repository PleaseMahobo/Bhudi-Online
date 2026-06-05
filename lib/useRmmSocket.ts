"use client";

import { useEffect, useRef, useState } from "react";

export interface DeviceEvent {
  device_id: string;
  status: "online" | "offline";
  last_seen?: string;
}

export interface CommandEvent {
  command_id: string;
  output: string;
  exit_code: number;
}

export function useRmmSocket(url: string) {
  const ws = useRef<WebSocket | null>(null);
  const [devices, setDevices] = useState<Record<string, DeviceEvent>>({});
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // DEVICE UPDATE
      if (data.device_id && data.status) {
        setDevices((prev) => ({
          ...prev,
          [data.device_id]: data,
        }));
      }

      // COMMAND OUTPUT
      if (data.command_id) {
        setLogs((prev) => [...prev, data]);
      }
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  return { devices, logs, ws };
}