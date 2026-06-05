"use client";

import { useState } from "react";
import { sendCommand } from "@/lib/api";

export default function CommandsPage() {
  const [deviceId, setDeviceId] = useState("");
  const [command, setCommand] = useState("");

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold">Global Command Center</h1>

      <input
        placeholder="Device ID"
        value={deviceId}
        onChange={(e) => setDeviceId(e.target.value)}
        className="border p-2 block mt-3"
      />

      <input
        placeholder="Command"
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        className="border p-2 block mt-3"
      />

      <button
        onClick={() => sendCommand(Number(deviceId), command)}
        className="bg-green-600 text-white px-4 py-2 mt-3"
      >
        Execute
      </button>
    </div>
  );
}