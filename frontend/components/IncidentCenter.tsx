"use client";

export interface Incident {
  id: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "open" | "investigating" | "resolved";
  deviceCount: number;
  alertCount: number;
  timestamp: string;
}

interface Props {
  incidents: Incident[];
}

export default function IncidentCenter({ incidents }: Props) {
  const color = (s: string) => {
    switch (s) {
      case "critical":
        return "text-red-400";
      case "high":
        return "text-orange-400";
      case "medium":
        return "text-yellow-400";
      default:
        return "text-blue-400";
    }
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 h-full">
      <h2 className="text-white font-bold mb-4">
        Incident Center
      </h2>

      <div className="space-y-3 overflow-y-auto h-[420px]">
        {incidents.map((i) => (
          <div
            key={i.id}
            className="border border-slate-800 bg-slate-900 p-3 rounded"
          >
            <div className="flex justify-between">
              <p className={`text-sm font-semibold ${color(i.severity)}`}>
                {i.title}
              </p>

              <span className="text-xs text-slate-400">
                {i.status}
              </span>
            </div>

            <div className="text-xs text-slate-400 mt-1">
              Devices: {i.deviceCount} • Alerts: {i.alertCount}
            </div>

            <div className="text-xs text-slate-500 mt-1">
              {i.timestamp}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}