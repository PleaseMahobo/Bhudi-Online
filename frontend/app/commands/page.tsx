"use client";

import { useState } from "react";
import ModuleShell from "@/shared/components/ModuleShell";

async function sendCommand(deviceId: number, command: string) {
  try {
    await fetch(`/api/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deviceId, command }),
    });
  } catch (err) {
    console.error(err);
  }
}

export default function CommandsPage() {
  const [deviceId, setDeviceId] = useState("");
  const [command, setCommand] = useState("");

  return (
    <ModuleShell title="Commands" subtitle="Global command center">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm max-w-lg space-y-4">
        <input
          placeholder="Device ID"
          value={deviceId}
          onChange={(e) => setDeviceId(e.target.value)}
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <input
          placeholder="Command"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="button"
          onClick={() => sendCommand(Number(deviceId), command)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          Execute
        </button>
      </div>
    </ModuleShell>
  );
}
