"use client";

import { useState } from "react";

// Local fallback implementation for sending commands to the backend API.
// The project previously attempted to import sendCommand from @/lib/api,
// but that symbol is not exported. Keep a small client-side helper here
// to avoid touching other files.
async function sendCommand(deviceId: number, command: string) {
  try {
    await fetch(`/api/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deviceId, command }),
    });
  } catch (err) {
    // noop - keep UI simple; errors could be surfaced later
    console.error(err);
  }
}

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