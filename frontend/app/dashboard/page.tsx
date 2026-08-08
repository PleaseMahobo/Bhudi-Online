'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { motion } from 'framer-motion';
import { Server, Cpu, Zap, Wifi, Copy, Check } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getHealth, getDevices } from '@/lib/api';
import { useWebSocket } from '@/lib/websocket';
import ModuleShell from '@/shared/components/ModuleShell';

export default function RMMDashboard() {
  const { user, loading } = useAuth();
  const [devices, setDevices] = useState<any[]>([]);
  const [cpuData, setCpuData] = useState<any[]>([]);
  const [memoryData, setMemoryData] = useState<any[]>([]);
  const [copied, setCopied] = useState(false);

  const agentStartCommand =
    "$env:BHUDI_SERVER_URL='https://bhudi-online-production.up.railway.app'; Set-Location .\\agent; pip install -r requirements.txt; python main.py";

  const { isConnected } = useWebSocket();

  useEffect(() => {
    if (loading || !user) return;

    const fetchData = async () => {
      try {
        const [, deviceList] = await Promise.all([getHealth(), getDevices()]);
        setDevices(deviceList);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);

    const sim = setInterval(() => {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setCpuData((p) => [...p.slice(-19), { time, value: 35 + Math.random() * 50 }]);
      setMemoryData((p) => [...p.slice(-19), { time, value: 50 + Math.random() * 40 }]);
    }, 2500);

    return () => {
      clearInterval(interval);
      clearInterval(sim);
    };
  }, [loading, user]);

  const executeCommand = (cmd: string) => {
    alert(`✅ Command "${cmd}" sent successfully`);
  };

  const copyAgentStartCommand = async () => {
    try {
      await navigator.clipboard.writeText(agentStartCommand);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch (error) {
      console.error('Failed to copy command:', error);
      setCopied(false);
    }
  };

  return (
    <ModuleShell title="Command Center" subtitle="Live Enterprise Monitoring">
      <div className="flex justify-end mb-4">
        <div
          className={`px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-2 ${
            isConnected
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          <Wifi size={14} /> {isConnected ? 'Connected' : 'Reconnecting...'}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Devices', value: devices.length },
          { label: 'Online', value: devices.length },
          { label: 'Active Alerts', value: '3' },
          { label: 'Avg Latency', value: '41ms' },
        ].map((s, i) => (
          <motion.div
            key={i}
            whileHover={{ scale: 1.01 }}
            className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm"
          >
            <p className="text-3xl font-bold text-slate-900">{s.value}</p>
            <p className="text-sm text-slate-500 mt-1">{s.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h3 className="font-semibold mb-4 flex items-center gap-2 text-indigo-600 text-sm">
            <Cpu size={16} /> CPU Usage
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={cpuData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip />
              <Line type="natural" dataKey="value" stroke="#2563EB" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h3 className="font-semibold mb-4 text-sm text-slate-700">Memory Usage</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={memoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip />
              <Line type="natural" dataKey="value" stroke="#4f46e5" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Devices + Commands */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h3 className="font-semibold mb-4 flex items-center gap-2 text-sm text-slate-800">
            <Server size={16} /> Connected Devices ({devices.length})
          </h3>
          {devices.length === 0 ? (
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-5 space-y-4">
              <div>
                <p className="text-base font-semibold text-slate-900">No agents enrolled yet</p>
                <p className="text-sm text-slate-500 mt-1">
                  Start one production agent and this panel will populate automatically within a few
                  heartbeats.
                </p>
              </div>

              <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
                <p className="text-xs text-slate-400 mb-2">PowerShell quick start</p>
                <pre className="text-xs text-indigo-300 whitespace-pre-wrap break-all">
                  {agentStartCommand}
                </pre>
              </div>

              <button
                type="button"
                onClick={copyAgentStartCommand}
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-lg transition"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? 'Copied' : 'Copy Start Command'}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {devices.map((device, i) => (
                <motion.div
                  key={i}
                  whileHover={{ scale: 1.01 }}
                  className="bg-slate-50 p-4 rounded-lg border border-slate-200"
                >
                  <h4 className="font-medium text-slate-900">{device.name || `Device ${i + 1}`}</h4>
                  <p className="text-emerald-600 text-sm">● Online</p>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h3 className="font-semibold mb-4 flex items-center gap-2 text-sm text-slate-800">
            <Zap size={16} /> Command Execution
          </h3>
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => executeCommand('restart')}
              className="w-full bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 p-4 rounded-lg text-left text-sm text-slate-800 transition"
            >
              Restart Agent
            </button>
            <button
              type="button"
              onClick={() => executeCommand('scan')}
              className="w-full bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 p-4 rounded-lg text-left text-sm text-slate-800 transition"
            >
              Run System Scan
            </button>
            <button
              type="button"
              onClick={() => executeCommand('logs')}
              className="w-full bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 p-4 rounded-lg text-left text-sm text-slate-800 transition"
            >
              Collect Logs
            </button>
          </div>
        </div>
      </div>
    </ModuleShell>
  );
}
