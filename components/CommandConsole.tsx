"use client";

import React, { useState } from "react";

export default function CommandConsole({ ws }: any) {
  const [deviceId, setDeviceId] = useState("");
  const [command, setCommand] = useState("");

  const sendCommand = () => {
    if (!ws.current) return;

    ws.current.send(
      JSON.stringify({
        type: "command",
        device_id: deviceId,
        command: command,
      })
    );

    setCommand("");
  };

  return (
    <div className="p-4 border rounded-xl space-y-2">
      <input
        className="border p-2 w-full"
        placeholder="Device ID"
        value={deviceId}
        onChange={(e) => setDeviceId(e.target.value)}
      />

      <input
        className="border p-2 w-full"
        placeholder="Command (e.g. whoami)"
        value={command}
        onChange={(e) => setCommand(e.target.value)}
      />

      <button
        onClick={sendCommand}
        className="bg-blue-600 text-white px-4 py-2 rounded"
      >
        Execute
      </button>
    </div>
  );
}