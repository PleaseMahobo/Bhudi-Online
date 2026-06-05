"use client";

import { useEffect, useState } from "react";
import { getDevices } from "@/lib/api";
import DeviceCard from "@/components/DeviceCard";

export default function Dashboard() {
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const data = await getDevices();
    setDevices(data);
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">RMM Dashboard</h1>

      <div className="grid grid-cols-3 gap-4">
        {devices.map((d: any) => (
          <DeviceCard key={d.id} device={d} />
        ))}
      </div>
    </div>
  );
}