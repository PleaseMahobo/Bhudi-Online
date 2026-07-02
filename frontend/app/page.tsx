'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Server, AlertTriangle, Cpu, Zap, Users, Shield, Eye } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function RMMDashboard() {
  const [health, setHealth] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([
    { id: 1, message: "High CPU detected on Endpoint-03", severity: "high", time: "2m ago" },
    { id: 2, message: "New agent connected", severity: "info", time: "17m ago" },
  ]);

  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);

  useEffect(() => {
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
    }, 2500);

    return () => {
      clearInterval(interval);
      clearInterval(metricInterval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white flex">
      {/* Sidebar */}
      <div className="w-72 bg-[#111827] border-r border-[#1e2937] p-6 fixed h-screen overflow-auto">
        <div className="flex items-center gap-3 mb-12">
          <div className="w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-600 rounded-2xl flex items-center justify-center font-bold text-3xl shadow-xl shadow-sky-500/50">B</div>
          <div>
            <h1 className="text-3xl font-bold tracking-tighter">BHUDI</h1>
            <p className="text-sky-400 text-sm -mt-1">RMM PLATFORM</p>
          </div>
        </div>

        <nav className="space-y-1">
          {['Dashboard', 'Devices', 'Live Alerts', 'Command Center', 'Analytics', 'Settings'].map((item, i) => (
            <a key={i} href="#" className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all ${i === 0 ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/30' : 'hover:bg-zinc-800 text-zinc-300'}`}>
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
              <h1 className="text-5xl font-bold tracking-tighter">Command Center</h1>
              <p className="text-sky-400">Enterprise Remote Monitoring & Management</p>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" /> ALL SYSTEMS LIVE
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            {[
              { label: "Total Devices", value: devices.length, icon: Server },
              { label: "Online", value: devices.length, icon: Activity, color: "emerald" },
              { label: "Active Alerts", value: alerts.length, icon: AlertTriangle, color: "amber" },
              { label: "Avg Latency", value: "41ms", icon: Zap, color: "sky" },
            ].map((stat, i) => (
              <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6">
                <stat.icon className={`mb-4 ${stat.color ? `text-${stat.color}-400` : 'text-sky-400'}`} size={32} />
                <p className="text-5xl font-bold mt-2">{stat.value}</p>
                <p className="text-zinc-400 mt-1">{stat.label}</p>
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
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            {/* Quick Command Panel */}
            <div className="lg:col-span-2 bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Zap className="text-amber-400" /> Quick Actions</h3>
              <div className="space-y-3">
                <button className="w-full bg-zinc-800 hover:bg-zinc-700 p-4 rounded-2xl text-left transition">Restart Remote Agent</button>
                <button className="w-full bg-zinc-800 hover:bg-zinc-700 p-4 rounded-2xl text-left transition">Run Full System Scan</button>
                <button className="w-full bg-zinc-800 hover:bg-zinc-700 p-4 rounded-2xl text-left transition">Collect Logs</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}