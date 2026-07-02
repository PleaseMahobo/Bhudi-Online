// frontend/app/dashboard/page.tsx
'use client';

import React, { useEffect, useState } from 'react';
<<<<<<< HEAD
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
=======

export default function Dashboard() {
  const [backendStatus, setBackendStatus] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);

  useEffect(() => {
    fetchBackendStatus();
    fetchDevices();
  }, []);
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5

  const fetchBackendStatus = async () => {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      setBackendStatus(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/devices/status');
      const data = await res.json();
      setDevices(data.devices || []);
    } catch (err) {
      console.error(err);
    }
  };

  return (
<<<<<<< HEAD
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
=======
    <div className="min-h-screen bg-zinc-950 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Bhudi RMM Dashboard</h1>

        {/* Backend Status */}
        <div className="bg-zinc-900 p-6 rounded-xl mb-8">
          <h2 className="text-xl font-semibold mb-4">Backend Status</h2>
          <pre className="bg-black p-4 rounded-lg overflow-auto text-sm">
            {JSON.stringify(backendStatus, null, 2)}
          </pre>
        </div>

        {/* Devices */}
        <div className="bg-zinc-900 p-6 rounded-xl">
          <h2 className="text-xl font-semibold mb-4">Devices ({devices.length})</h2>
          {devices.length === 0 ? (
            <p className="text-gray-400">No devices connected yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {devices.map((device, i) => (
                <div key={i} className="bg-zinc-800 p-4 rounded-lg">
                  <p className="font-medium">{device.name || 'Unknown Device'}</p>
                  <p className="text-sm text-green-400">Online</p>
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
