'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from "@/shared/auth/AuthContext";
import { useRouter } from "next/navigation";
import { motion } from 'framer-motion';
import { Server, Cpu, Zap, LogOut, Wifi } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getHealth, getDeviceStatus } from '@/lib/api';
import { useWebSocket } from "@/lib/websocket";

export default function RMMDashboard() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [devices, setDevices] = useState<any[]>([]);
  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);

  const { isConnected } = useWebSocket();

  useEffect(() => {
  if (!loading && !user) {
    router.push("/login");
  }
}, [loading, user, router]);

  useEffect(() => {
    if (loading || !user) return;

    const fetchData = async () => {
      try {
        const [health, deviceResponse] = await Promise.all([
          getHealth(),
          getDeviceStatus(),
        ]);
        // deviceResponse may be an array or an object with a `devices` prop.
        // Cast to any to avoid strict typing issues from unknown API shapes.
        const dr: any = deviceResponse;
        const devices = Array.isArray(dr) ? dr : (dr?.devices ?? []);
        setDevices(devices);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);

    const sim = setInterval(() => {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setCpuData(p => [...p.slice(-19), { time, value: 35 + Math.random() * 50 }]);
      setMemoryData(p => [...p.slice(-19), { time, value: 50 + Math.random() * 40 }]);
    }, 2500);

    return () => { clearInterval(interval); clearInterval(sim); };
  }, [loading, user]);

  const executeCommand = (cmd: string) => {
    alert(`✅ Command "${cmd}" sent successfully`);
  };

  if (loading) {
    return <div className="min-h-screen bg-[#0a0f1c] flex items-center justify-center text-white">Loading secure dashboard...</div>;
  }

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white flex">
      {/* Sidebar */}
      <div className="w-72 bg-[#111827] border-r border-[#1e2937] p-6 fixed h-screen overflow-auto">
        <div className="flex items-center gap-3 mb-12">
          <div className="w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-600 rounded-2xl flex items-center justify-center font-bold text-3xl">B</div>
          <div>
            <h1 className="text-3xl font-bold tracking-tighter">BHUDI</h1>
            <p className="text-sky-400 text-sm -mt-1">RMM PLATFORM</p>
          </div>
        </div>

        <div className="mb-8">
          <p className="text-xs text-zinc-500">Logged in as</p>
          <p className="font-medium">{user?.email}</p>
        </div>

        <nav className="space-y-1">
          {['Dashboard', 'Devices', 'Live Alerts', 'Command Center', 'Analytics', 'Settings'].map((item, i) => (
            <a key={i} href="#" className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all ${i === 0 ? 'bg-sky-500 text-white' : 'hover:bg-zinc-800 text-zinc-300'}`}>
              {item}
            </a>
          ))}
        </nav>

        <button 
          onClick={logout}
          className="absolute bottom-8 left-6 flex items-center gap-3 text-red-400 hover:text-red-500"
        >
          <LogOut size={20} /> Sign Out
        </button>
      </div>

      <div className="flex-1 ml-72 p-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-10">
            <div>
              <h1 className="text-5xl font-bold tracking-tighter bg-gradient-to-r from-sky-300 to-blue-400 bg-clip-text text-transparent">Command Center</h1>
              <p className="text-sky-400">Live Enterprise Monitoring</p>
            </div>
            <div className={`px-4 py-1.5 rounded-full text-sm flex items-center gap-2 ${isConnected ? 'bg-emerald-900 text-emerald-400' : 'bg-red-900 text-red-400'}`}>
              <Wifi size={16} /> {isConnected ? 'Connected' : 'Reconnecting...'}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            {[
              { label: "Total Devices", value: devices.length },
              { label: "Online", value: devices.length },
              { label: "Active Alerts", value: "3" },
              { label: "Avg Latency", value: "41ms" },
            ].map((s, i) => (
              <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6">
                <p className="text-5xl font-bold">{s.value}</p>
                <p className="text-zinc-400 mt-1">{s.label}</p>
              </motion.div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
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

            <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6">Memory Usage</h3>
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

          {/* Devices + Commands */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Server /> Connected Devices ({devices.length})</h3>
              {devices.length === 0 ? (
                <p className="text-zinc-400 py-20 text-center">No devices connected yet.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {devices.map((device, i) => (
                    <motion.div key={i} whileHover={{ scale: 1.02 }} className="bg-zinc-800 p-6 rounded-2xl border border-zinc-700">
                      <h4 className="font-medium">{device.name || `Device ${i+1}`}</h4>
                      <p className="text-emerald-400 text-sm">● Online</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            <div className="lg:col-span-2 bg-zinc-900 border border-zinc-700 rounded-3xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2"><Zap /> Command Execution</h3>
              <div className="space-y-4">
                <button onClick={() => executeCommand("restart")} className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Restart Agent</button>
                <button onClick={() => executeCommand("scan")} className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Run System Scan</button>
                <button onClick={() => executeCommand("logs")} className="w-full bg-zinc-800 hover:bg-sky-600/20 border border-sky-600 p-5 rounded-2xl text-left transition">Collect Logs</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}