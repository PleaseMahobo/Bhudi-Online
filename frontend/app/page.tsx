'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from "@/shared/auth/AuthContext";
import { useRouter } from "next/navigation";
import { motion } from 'framer-motion';
import { Activity, Server, AlertTriangle, Cpu, Zap } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getHealth, getDeviceStatus } from '@/lib/api';

export default function RMMDashboard() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [health, setHealth] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;

    const fetchData = async () => {
      try {
        const [h, d] = await Promise.all([
          getHealth(),
          getDeviceStatus()
        ]);
        setHealth(h);
        // getDeviceStatus may return an array of devices or an object with a `devices` field
        setDevices(Array.isArray(d) ? d : (d && (d as any).devices) ? (d as any).devices : []);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
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
  }, [user]);

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
      </div>

      <div className="flex-1 ml-72 p-10">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-5xl font-bold tracking-tighter mb-2">Command Center</h1>
          <p className="text-sky-400 mb-10">Live Enterprise Monitoring</p>

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

          {/* Charts and other sections as before */}
        </div>
      </div>
    </div>
  );
}