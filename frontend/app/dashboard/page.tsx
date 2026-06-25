// frontend/app/dashboard/page.tsx
'use client';

import React, { useEffect, useState } from 'react';

export default function Dashboard() {
  const [backendStatus, setBackendStatus] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);

  useEffect(() => {
    fetchBackendStatus();
    fetchDevices();
  }, []);

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
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
