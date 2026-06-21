'use client';

import React, { useEffect, useState } from 'react';
// framer-motion may not be available in all environments; use a plain div instead
import { Activity, Server, AlertTriangle, Cpu, Zap } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function RMMDashboard() {
  const [health, setHealth] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [healthRes, devicesRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`, { cache: 'no-store' }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/devices/status`, { cache: 'no-store' })
        ]);

        if (healthRes.ok) setHealth(await healthRes.json());
        if (devicesRes.ok) {
          const data = await devicesRes.json();
          setDevices(data.devices || data || []);
        }
      } catch (err) {
        console.error("Fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);

    // Simulate live metrics
    const sim = setInterval(() => {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setCpuData(p => [...p.slice(-19), { time, value: 35 + Math.random() * 50 }]);
      setMemoryData(p => [...p.slice(-19), { time, value: 50 + Math.random() * 40 }]);
    }, 2500);

    return () => { clearInterval(interval); clearInterval(sim); };
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white flex">
      {/* Sidebar */}
      <div className="w-72 bg-[#111827] border-r border-[#1e2937] p-6 fixed h-screen">
        <div className="flex items-center gap-3 mb-12">
          <div className="w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-600 rounded-2xl flex items-center justify-center font-bold text-3xl">B</div>
          <div>
            <h1 className="text-3xl font-bold tracking-tighter">BHUDI</h1>
            <p className="text-sky-400 text-sm -mt-1">RMM PLATFORM</p>
          </div>
        </div>

        <nav className="space-y-1">
          {['Dashboard', 'Devices', 'Alerts', 'Commands', 'Analytics', 'Settings'].map((item, i) => (
            <a key={i} href="#" className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all ${i === 0 ? 'bg-sky-500 text-white' : 'hover:bg-zinc-800 text-zinc-300'}`}>
              {item}
            </a>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 ml-72 p-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-10">
            <h1 className="text-5xl font-bold tracking-tighter">Command Center</h1>
            <div className="flex items-center gap-2 text-emerald-400">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></div>
              LIVE
            </div>
          </div>

          {/* Backend Status */}
          <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Backend Status</h2>
            <pre className="bg-black p-4 rounded-2xl text-sm overflow-auto">
              {JSON.stringify(health, null, 2) || "Connecting..."}
            </pre>
          </div>

          {/* Real-time Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Cpu className="text-sky-400" /> CPU Usage</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={cpuData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Line type="natural" dataKey="value" stroke="#38bdf8" strokeWidth={4} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6">Memory Usage</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={memoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Line type="natural" dataKey="value" stroke="#22d3ee" strokeWidth={4} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Devices */}
          <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
            <h2 className="text-xl font-semibold mb-6">Connected Devices ({devices.length})</h2>
            {devices.length === 0 ? (
              <p className="text-zinc-400 py-20 text-center text-lg">No devices connected yet.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {devices.map((device, i) => (
                  <div key={i} className="bg-zinc-800 p-6 rounded-2xl border border-zinc-700 hover:scale-[1.02] transition-transform">
                    <div className="flex justify-between">
                      <h3 className="font-medium">{device.name || `Device ${i+1}`}</h3>
                      <span className="text-emerald-400">● Online</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}