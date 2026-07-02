'use client';

import React, { useEffect, useState } from 'react';
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [health, setHealth] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  useEffect(() => {
    if (status !== "authenticated") return;

    const fetchData = async () => {
      try {
        const [healthRes, devicesRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/devices/status`)
        ]);

        if (healthRes.ok) setHealth(await healthRes.json());
        if (devicesRes.ok) {
          const data = await devicesRes.json();
          setDevices(data.devices || data || []);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [status]);

  if (status === "loading" || loading) {
    return <div className="min-h-screen bg-[#0a0f1c] flex items-center justify-center text-white">Loading Dashboard...</div>;
  }

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Bhudi RMM Dashboard</h1>

        <div className="bg-zinc-900 p-6 rounded-xl mb-8">
          <h2 className="text-xl font-semibold mb-4">Backend Status</h2>
          <pre className="bg-black p-4 rounded-lg overflow-auto text-sm">
            {JSON.stringify(health, null, 2)}
          </pre>
        </div>

        <div className="bg-zinc-900 p-6 rounded-xl">
          <h2 className="text-xl font-semibold mb-4">Devices ({devices.length})</h2>
          {devices.length === 0 ? (
            <p className="text-gray-400 py-8">No devices connected yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {devices.map((device, i) => (
                <div key={i} className="bg-zinc-800 p-4 rounded-lg">
                  <p className="font-medium">{device.name || 'Device'}</p>
                  <p className="text-green-400 text-sm">Online</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}