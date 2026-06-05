"use client";

import { useRmmSocket } from "@/lib/useRmmSocket";
import Sidebar from "@/components/soc/Sidebar";
import TopBar from "@/components/soc/TopBar";
import DevicePanel from "@/components/soc/DevicePanel";
import { useState } from "react";

const ActivityFeed = ({ logs }: { logs: any }) => (
  <div className="space-y-3">
    <h2 className="text-lg font-semibold mb-3">Activity Feed</h2>
    {Array.isArray(logs) && logs.length > 0 ? (
      logs.map((log: any, index: number) => (
        <div key={index} className="rounded-lg border border-gray-800 p-3">
          <div className="text-sm text-gray-300">
            {log.message ?? JSON.stringify(log)}
          </div>
        </div>
      ))
    ) : (
      <div className="text-sm text-gray-500">No activity logs available.</div>
    )}
  </div>
);

const CommandConsole = ({ ws }: { ws: any }) => (
  <div className="border-t border-gray-800 p-4">
    Command console component not available
  </div>
);

export default function Dashboard() {
  const { devices, logs, ws } = useRmmSocket(
    "ws://localhost:8000/ws/dashboard"
  );

  const onlineCount = Array.isArray(devices)
  ? devices.filter((d: any) => d.status === "online").length
  : 0;
  const [selectedDevice, setSelectedDevice] = useState(null);

  return (
    <div className="h-screen flex bg-[#0b0f19] text-white overflow-hidden">

      <Sidebar />

      <div className="flex flex-col flex-1">

        <TopBar onlineCount={onlineCount} devices={devices} />

        {/* MAIN SOC WORKSPACE */}
        <div className="flex flex-1 overflow-hidden">

          {/* DEVICE OPS ZONE */}
          <div className="flex-1 p-4 overflow-auto">
            <DevicePanel devices={devices} />
          </div>

          {/* LIVE OPERATIONS FEED */}
          <div className="w-[380px] border-l border-gray-800 p-4 overflow-auto">
            <ActivityFeed logs={logs} />
          </div>

        </div>

        {/* COMMAND STRIP (FIXED OPERATOR CONSOLE) */}
        <CommandConsole ws={ws} />

      </div>
    </div>
  );
}