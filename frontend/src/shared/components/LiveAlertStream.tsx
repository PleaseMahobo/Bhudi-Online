'use client';

import { useAlertWebSocket, type LiveAlert } from '@/lib/useAlertWebSocket';
import { Wifi, WifiOff, Bell } from 'lucide-react';

function severityStyles(severity: string) {
  switch (severity) {
    case 'critical':
      return 'border-red-500/50 bg-red-950/40 text-red-300';
    case 'warning':
      return 'border-yellow-500/50 bg-yellow-950/40 text-yellow-300';
    case 'info':
      return 'border-sky-500/50 bg-sky-950/40 text-sky-300';
    default:
      return 'border-zinc-600 bg-zinc-800/60 text-zinc-300';
  }
}

function AlertCard({ alert }: { alert: LiveAlert }) {
  return (
    <div
      className={`border rounded-2xl p-4 ${severityStyles(alert.severity)} ${
        alert.resolved ? 'opacity-50' : ''
      } ${alert.suppressed ? 'opacity-60' : ''}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider">
            {alert.severity}
          </span>
          <span className="text-[10px] uppercase opacity-70">{alert.alert_type}</span>
          {alert.suppressed && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-300">
              suppressed
            </span>
          )}
          {alert.resolved && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-900 text-emerald-300">
              resolved
            </span>
          )}
        </div>
        <span className="text-[10px] opacity-60">
          {alert.created_at
            ? new Date(alert.created_at).toLocaleTimeString()
            : ''}
        </span>
      </div>

      <p className="mt-2 text-sm">{alert.message}</p>

      <div className="mt-2 flex flex-wrap gap-2 text-[10px] opacity-70">
        <span>{alert.provider}</span>
        {alert.escalation_level != null && alert.escalation_level > 0 && (
          <span>Escalation L{alert.escalation_level}</span>
        )}
        {alert.correlated_count != null && alert.correlated_count > 1 && (
          <span>×{alert.correlated_count} correlated</span>
        )}
        {alert.context?.rule_name && <span>Rule: {alert.context.rule_name}</span>}
      </div>
    </div>
  );
}

export default function LiveAlertStream() {
  const { alerts, isConnected, clearAlerts } = useAlertWebSocket(true);

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bell size={18} className="text-sky-400" />
          <h2 className="font-semibold">Live Alert Stream</h2>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${
              isConnected
                ? 'bg-emerald-900/50 text-emerald-400'
                : 'bg-red-900/50 text-red-400'
            }`}
          >
            {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {isConnected ? 'Live' : 'Reconnecting'}
          </span>
          {alerts.length > 0 && (
            <button
              onClick={clearAlerts}
              className="text-xs text-zinc-400 hover:text-zinc-200"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 max-h-[480px] pr-1">
        {alerts.length === 0 && (
          <div className="text-sm text-zinc-500 py-8 text-center">
            Waiting for alerts…
            <br />
            <span className="text-xs">Connected clients receive events instantly</span>
          </div>
        )}
        {alerts.map((alert) => (
          <AlertCard key={alert.id} alert={alert} />
        ))}
      </div>
    </div>
  );
}
