"use client";

import { useState } from "react";
import { sendCommand } from "@/lib/api";

export default function CommandPanel({ deviceId }: any) {
  const [cmd, setCmd] = useState("");

  async function runCommand() {
    await sendCommand(deviceId, cmd);
    setCmd("");
  }

  return (
    <div className="mt-3">
      <input
        className="border p-1 w-full"
        placeholder="Enter command..."
        value={cmd}
        onChange={(e) => setCmd(e.target.value)}
      />

      <button
        onClick={runCommand}
        className="bg-blue-600 text-white px-2 py-1 mt-2 rounded"
      >
        Run
      </button>
    </div>
  );
}