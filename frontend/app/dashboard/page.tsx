'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Server, AlertTriangle, Cpu, Zap } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function RMMDashboard() {
  const [health, setHealth] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);

  const fetchLiveData = async () => {
    try {
      setError(null);
      const [healthRes, devicesRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`, { cache: 'no-store' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/devices/status`, { cache: 'no-store' })
      ]);

      if (healthRes.ok) {
        setHealth(await healthRes.json());
      } else {
        setError("Backend health check failed");
      }

      if (devicesRes.ok) {
        const data = await devicesRes.json();
        setDevices(data.devices || data || []);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveData();
    const interval = setInterval(fetchLiveData, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  // Simple live simulation for charts (you can replace with real backend metrics later)
  useEffect(() => {
    const interval = setInterval(() => {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setCpuData(prev => [...prev.slice(-19), { time, value: 30 + Math.random() * 60 }]);
      setMemoryData(prev => [...prev.slice(-19), { time, value: 45 + Math.random() * 45 }]);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="min-h-screen bg-[#0a0f1c] flex items-center justify-center text-white">Loading Live Dashboard...</div>;
  }

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
          {['Dashboard', 'Devices', 'Live Alerts', 'Command Center', 'Analytics', 'Settings'].map((item, i) => (
            <a key={i} href="#" className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all ${i === 0 ? 'bg-sky-500 text-white' : 'hover:bg-zinc-800 text-zinc-300'}`}>
              {item}
            </a>
          ))}
        </nav>
      </div>

      <div className="flex-1 ml-72 p-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-10">
            <div>
              <h1 className="text-5xl font-bold tracking-tighter">Command Center</h1>
              <p className="text-sky-400">Live Enterprise Monitoring</p>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" /> LIVE
            </div>
          </div>

          {error && (
            <div className="bg-red-900/50 border border-red-700 p-4 rounded-2xl mb-8">
              {error}
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            {[
              { label: "Total Devices", value: devices.length },
              { label: "Online", value: devices.length },
              { label: "Active Alerts", value: "3" },
              { label: "Avg Latency", value: "42ms" },
            ].map((s, i) => (
              <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6">
                <p className="text-5xl font-bold">{s.value}</p>
                <p className="text-zinc-400 mt-1">{s.label}</p>
              </motion.div>
            ))}
          </div>

          {/* Real-time Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Cpu className="text-sky-400" /> CPU Usage</h3>
              <ResponsiveContainer width="100%" height={300}>
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
              <ResponsiveContainer width="100%" height={300}>
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
              <p className="text-zinc-400 py-20 text-center">No devices connected yet. Deploy agents to begin monitoring.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {devices.map((device, i) => (
                  <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-zinc-800 p-6 rounded-2xl border border-zinc-700">
                    <h4 className="font-medium">{device.name || `Device ${i+1}`}</h4>
                    <p className="text-emerald-400 text-sm">● Online</p>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
}
