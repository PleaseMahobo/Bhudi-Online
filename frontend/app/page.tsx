'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
<<<<<<< HEAD
import { Activity, Server, AlertTriangle, Cpu, Zap, Users, Shield, Eye } from 'lucide-react';
=======
import { Activity, Server, AlertTriangle, Cpu, Zap, Users, Shield } from 'lucide-react';
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function RMMDashboard() {
  const [health, setHealth] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
<<<<<<< HEAD
  const [alerts, setAlerts] = useState<any[]>([
    { id: 1, message: "High CPU detected on Endpoint-03", severity: "high", time: "2m ago" },
    { id: 2, message: "New agent connected", severity: "info", time: "17m ago" },
  ]);
=======
  const [loading, setLoading] = useState(true);
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5

  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);

  useEffect(() => {
<<<<<<< HEAD
    const fetchData = async () => {
      try {
        const [hRes, dRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/devices/status`)
        ]);

        if (hRes.ok) setHealth(await hRes.json());
        if (dRes.ok) {
          const data = await dRes.json();
          setDevices(data.devices || data || []);
        }
      } catch (err) {
        console.error(err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);

    // Simulate real-time metrics
    const metricInterval = setInterval(() => {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setCpuData(prev => [...prev.slice(-19), { time, value: 35 + Math.random() * 45 }]);
      setMemoryData(prev => [...prev.slice(-19), { time, value: 50 + Math.random() * 40 }]);
=======
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
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
    }, 2500);

    return () => {
      clearInterval(interval);
<<<<<<< HEAD
      clearInterval(metricInterval);
=======
      clearInterval(metricsInterval);
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white flex">
<<<<<<< HEAD
      {/* Sidebar */}
      <div className="w-72 bg-[#111827] border-r border-[#1e2937] p-6 fixed h-screen overflow-auto">
        <div className="flex items-center gap-3 mb-12">
          <div className="w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-600 rounded-2xl flex items-center justify-center font-bold text-3xl shadow-xl shadow-sky-500/50">B</div>
          <div>
            <h1 className="text-3xl font-bold tracking-tighter">BHUDI</h1>
=======
      {/* Sidebar - Metallic Blue Theme */}
      <div className="w-72 bg-[#0f172a] border-r border-[#1e3a8a] p-6 fixed h-screen overflow-auto">
        <div className="flex items-center gap-3 mb-12">
          <div className="w-12 h-12 bg-gradient-to-br from-sky-300 via-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center font-bold text-3xl shadow-xl shadow-blue-500/50">B</div>
          <div>
            <h1 className="text-3xl font-bold tracking-tighter text-white">BHUDI</h1>
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
            <p className="text-sky-400 text-sm -mt-1">RMM PLATFORM</p>
          </div>
        </div>

        <nav className="space-y-1">
          {['Dashboard', 'Devices', 'Live Alerts', 'Command Center', 'Analytics', 'Settings'].map((item, i) => (
<<<<<<< HEAD
            <a key={i} href="#" className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all ${i === 0 ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/30' : 'hover:bg-zinc-800 text-zinc-300'}`}>
=======
            <a 
              key={i} 
              href="#" 
              className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all ${i === 0 ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-lg' : 'hover:bg-zinc-800 text-zinc-300'}`}
            >
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
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
<<<<<<< HEAD
              <h1 className="text-5xl font-bold tracking-tighter">Command Center</h1>
              <p className="text-sky-400">Enterprise Remote Monitoring & Management</p>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" /> ALL SYSTEMS LIVE
=======
              <h1 className="text-5xl font-bold tracking-tighter bg-gradient-to-r from-sky-300 to-blue-400 bg-clip-text text-transparent">Command Center</h1>
              <p className="text-sky-400">Live Enterprise Remote Monitoring</p>
            </div>
            <div className="flex items-center gap-3 text-emerald-400 font-medium">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" />
              ALL SYSTEMS LIVE
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            {[
              { label: "Total Devices", value: devices.length, icon: Server },
<<<<<<< HEAD
              { label: "Online", value: devices.length, icon: Activity, color: "emerald" },
              { label: "Active Alerts", value: alerts.length, icon: AlertTriangle, color: "amber" },
              { label: "Avg Latency", value: "41ms", icon: Zap, color: "sky" },
            ].map((stat, i) => (
              <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6">
                <stat.icon className={`mb-4 ${stat.color ? `text-${stat.color}-400` : 'text-sky-400'}`} size={32} />
                <p className="text-5xl font-bold mt-2">{stat.value}</p>
=======
              { label: "Online", value: devices.length, icon: Activity },
              { label: "Active Alerts", value: "3", icon: AlertTriangle },
              { label: "Avg Response", value: "39ms", icon: Zap },
            ].map((stat, i) => (
              <motion.div key={i} whileHover={{ scale: 1.03 }} className="bg-[#1e2937] border border-[#334155] rounded-3xl p-6">
                <stat.icon className="mb-4 text-sky-400" size={32} />
                <p className="text-5xl font-bold text-white">{stat.value}</p>
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
                <p className="text-zinc-400 mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </div>

          {/* Real-time Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
<<<<<<< HEAD
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Cpu className="text-sky-400" /> CPU Usage</h3>
              <ResponsiveContainer width="100%" height={300}>
=======
            <div className="bg-[#1e2937] border border-[#334155] rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2 text-sky-400"><Cpu /> CPU Usage</h3>
              <ResponsiveContainer width="100%" height={320}>
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
                <LineChart data={cpuData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Line type="natural" dataKey="value" stroke="#38bdf8" strokeWidth={4} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

<<<<<<< HEAD
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6">Memory Usage</h3>
              <ResponsiveContainer width="100%" height={300}>
=======
            <div className="bg-[#1e2937] border border-[#334155] rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2 text-sky-400">Memory Usage</h3>
              <ResponsiveContainer width="100%" height={320}>
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
                <LineChart data={memoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
<<<<<<< HEAD
                  <Line type="natural" dataKey="value" stroke="#22d3ee" strokeWidth={4} dot={false} />
=======
                  <Line type="natural" dataKey="value" stroke="#60a5fa" strokeWidth={4} dot={false} />
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

<<<<<<< HEAD
          {/* Devices & Quick Commands */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Server /> Connected Devices ({devices.length})</h3>
              {devices.length === 0 ? (
                <p className="text-zinc-400 py-20 text-center">No devices connected yet. Deploy agents to start monitoring.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {devices.map((device, i) => (
                    <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-zinc-800 p-6 rounded-2xl border border-zinc-700">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-medium">{device.name || `Endpoint ${i+1}`}</h4>
                          <p className="text-emerald-400 text-sm">● Online</p>
                        </div>
                        <button className="bg-sky-600 hover:bg-sky-500 px-4 py-2 rounded-xl text-sm">Command</button>
                      </div>
=======
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
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

<<<<<<< HEAD
            {/* Quick Command Panel */}
            <div className="lg:col-span-2 bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Zap className="text-amber-400" /> Quick Actions</h3>
              <div className="space-y-3">
                <button className="w-full bg-zinc-800 hover:bg-zinc-700 p-4 rounded-2xl text-left transition">Restart Remote Agent</button>
                <button className="w-full bg-zinc-800 hover:bg-zinc-700 p-4 rounded-2xl text-left transition">Run Full System Scan</button>
                <button className="w-full bg-zinc-800 hover:bg-zinc-700 p-4 rounded-2xl text-left transition">Collect Logs</button>
=======
            <div className="lg:col-span-2 bg-[#1e2937] border border-[#334155] rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2 text-sky-400"><Zap /> Quick Command Panel</h3>
              <div className="space-y-4">
                <button className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Restart Remote Agent</button>
                <button className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Run Full System Scan</button>
                <button className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Collect Logs</button>
>>>>>>> 4203add43249bd87f9817086888a01cd290a3ed5
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
