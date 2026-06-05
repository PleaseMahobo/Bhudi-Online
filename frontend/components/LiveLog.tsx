"use client";

import { useEffect, useState } from "react";
import { createSocket } from "@/lib/websocket";

export default function LiveLog({ deviceId }: any) {
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const ws = createSocket(deviceId, (data) => {
      if (data.type === "result") {
        setLogs((prev) => [...prev, data.result]);
      }
    });

    return () => ws.close();
  }, []);

  return (
    <div className="p-2 border mt-4 h-40 overflow-auto">
      {logs.map((l, i) => (
        <pre key={i}>{l}</pre>
      ))}
    </div>
  );
}