'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Activity, RefreshCw } from 'lucide-react';

type MetricPoint = {
  recorded_at?: string;
  cpu_percent?: number | null;
  memory_percent?: number | null;
  disk_percent?: number | null;
};

type Props = {
  deviceId: string;
  hostname?: string;
  minutes?: number;
  pollMs?: number;
  className?: string;
};

function fmtTick(iso?: string) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function DeviceMetricsChart({
  deviceId,
  hostname,
  minutes = 60,
  pollMs = 15000,
  className = '',
}: Props) {
  const [points, setPoints] = useState<MetricPoint[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!deviceId) return;
    try {
      setLoading(true);
      setError('');
      const res = await fetch(
        `/api/v1/metrics/devices/${encodeURIComponent(deviceId)}?minutes=${minutes}&limit=500`,
        { credentials: 'include', cache: 'no-store' }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || res.statusText);
      }
      setPoints(Array.isArray(data.points) ? data.points : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  }, [deviceId, minutes]);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), pollMs);
    return () => clearInterval(id);
  }, [load, pollMs]);

  const chartData = useMemo(
    () =>
      points.map((p) => ({
        t: fmtTick(p.recorded_at),
        full: p.recorded_at,
        cpu: p.cpu_percent ?? null,
        memory: p.memory_percent ?? null,
        disk: p.disk_percent ?? null,
      })),
    [points]
  );

  const latest = points[points.length - 1];

  return (
    <section className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Activity className="h-4 w-4 text-sky-600" />
          <span>{hostname || 'Device'} — metrics</span>
          <span className="text-xs font-normal text-slate-500">last {minutes}m</span>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </header>

      <div className="grid grid-cols-3 gap-3 px-5 pt-4 text-center">
        {[
          { label: 'CPU', value: latest?.cpu_percent, color: 'text-sky-600' },
          { label: 'Memory', value: latest?.memory_percent, color: 'text-violet-600' },
          { label: 'Disk', value: latest?.disk_percent, color: 'text-amber-600' },
        ].map((s) => (
          <div key={s.label} className="rounded-xl bg-slate-50 px-2 py-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{s.label}</div>
            <div className={`text-xl font-semibold tabular-nums ${s.color}`}>
              {s.value == null || Number.isNaN(Number(s.value)) ? '—' : `${Number(s.value).toFixed(0)}%`}
            </div>
          </div>
        ))}
      </div>

      <div className="h-64 w-full px-2 pb-4 pt-2">
        {error ? (
          <p className="px-4 py-8 text-center text-sm text-red-600">{error}</p>
        ) : chartData.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-slate-500">
            No metric samples yet. Keep the agent online — heartbeats fill this chart.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="t" tick={{ fontSize: 11, fill: '#64748b' }} minTickGap={24} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} width={36} unit="%" />
              <Tooltip
                contentStyle={{ borderRadius: 12, borderColor: '#e2e8f0', fontSize: 12 }}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.full || ''}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="cpu" name="CPU %" stroke="#0284c7" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="memory" name="Memory %" stroke="#7c3aed" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="disk" name="Disk %" stroke="#d97706" strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
