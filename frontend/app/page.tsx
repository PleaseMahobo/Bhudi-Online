// frontend/app/dashboard/page.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Server, AlertTriangle, Cpu, Zap, Users, Shield } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function RMMDashboard() {
  const [health, setHealth] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);

  useEffect(() => {
    const fetchLiveData = async () => {
      try {
        const [healthRes, devicesRes] = await Promise.all([
          fetch('/api/health', { cache: 'no-store' }),
          fetch('/api/devices/status', { cache: 'no-store' })
        ]);

        if (healthRes.ok) {
          const healthData = await healthRes.json();
          setHealth(healthData);
        }

        if (devicesRes.ok) {
          const data = await devicesRes.json();
          setDevices(data.devices || data || []);
        }
      } catch (err) {
        console.error("Live data fetch failed:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchLiveData();
    const interval = setInterval(fetchLiveData, 4000);

    // Live metrics simulation (replace with real backend data later)
    const metricsInterval = setInterval(() => {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setCpuData(prev => [...prev.slice(-19), { time, value: 32 + Math.random() * 55 }]);
      setMemoryData(prev => [...prev.slice(-19), { time, value: 48 + Math.random() * 42 }]);
    }, 2500);

    return () => {
      clearInterval(interval);
      clearInterval(metricsInterval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white flex">
      {/* Sidebar - Metallic Blue Theme */}
      <div className="w-72 bg-[#0f172a] border-r border-[#1e3a8a] p-6 fixed h-screen overflow-auto">
        <div className="flex items-center gap-3 mb-12">
          <div className="w-12 h-12 bg-gradient-to-br from-sky-300 via-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center font-bold text-3xl shadow-xl shadow-blue-500/50">B</div>
          <div>
            <h1 className="text-3xl font-bold tracking-tighter text-white">BHUDI</h1>
            <p className="text-sky-400 text-sm -mt-1">RMM PLATFORM</p>
          </div>
        </div>

        <nav className="space-y-1">
          {['Dashboard', 'Devices', 'Live Alerts', 'Command Center', 'Analytics', 'Settings'].map((item, i) => (
            <a 
              key={i} 
              href="#" 
              className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all ${i === 0 ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-lg' : 'hover:bg-zinc-800 text-zinc-300'}`}
            >
              {item}
            </a>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 ml-72 p-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-10">
            <div>
              <h1 className="text-5xl font-bold tracking-tighter bg-gradient-to-r from-sky-300 to-blue-400 bg-clip-text text-transparent">Command Center</h1>
              <p className="text-sky-400">Live Enterprise Remote Monitoring</p>
            </div>
            <div className="flex items-center gap-3 text-emerald-400 font-medium">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" />
              ALL SYSTEMS LIVE
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            {[
              { label: "Total Devices", value: devices.length, icon: Server },
              { label: "Online", value: devices.length, icon: Activity },
              { label: "Active Alerts", value: "3", icon: AlertTriangle },
              { label: "Avg Response", value: "39ms", icon: Zap },
            ].map((stat, i) => (
              <motion.div key={i} whileHover={{ scale: 1.03 }} className="bg-[#1e2937] border border-[#334155] rounded-3xl p-6">
                <stat.icon className="mb-4 text-sky-400" size={32} />
                <p className="text-5xl font-bold text-white">{stat.value}</p>
                <p className="text-zinc-400 mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </div>

          {/* Real-time Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            <div className="bg-[#1e2937] border border-[#334155] rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2 text-sky-400"><Cpu /> CPU Usage</h3>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={cpuData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Line type="natural" dataKey="value" stroke="#38bdf8" strokeWidth={4} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-[#1e2937] border border-[#334155] rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2 text-sky-400">Memory Usage</h3>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={memoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Line type="natural" dataKey="value" stroke="#60a5fa" strokeWidth={4} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Devices & Commands */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 bg-[#1e2937] border border-[#334155] rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2 text-sky-400"><Server /> Connected Devices ({devices.length})</h3>
              {devices.length === 0 ? (
                <p className="text-zinc-400 py-20 text-center">No devices connected yet. Deploy agents to begin monitoring.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {devices.map((device, i) => (
                    <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-[#0f172a] p-6 rounded-2xl border border-[#334155]">
                      <h4 className="font-medium text-lg">{device.name || `Device ${i+1}`}</h4>
                      <p className="text-emerald-400 text-sm">● Online</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            <div className="lg:col-span-2 bg-[#1e2937] border border-[#334155] rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2 text-sky-400"><Zap /> Quick Command Panel</h3>
              <div className="space-y-4">
                <button className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Restart Remote Agent</button>
                <button className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Run Full System Scan</button>
                <button className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Collect Logs</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
