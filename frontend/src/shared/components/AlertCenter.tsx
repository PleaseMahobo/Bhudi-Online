"use client";

export interface Alert {
  id: string;
  type: "critical" | "warning" | "info" | "recovery";
  message: string;
  device?: string;
  timestamp: string;
}

interface AlertCenterProps {
  alerts: Alert[];
}

export default function AlertCenter({ alerts }: AlertCenterProps) {
  const getAlertStyles = (type: Alert["type"]) => {
    switch (type) {
      case "critical":
        return "border-red-500 bg-red-950/30 text-red-300";
      case "warning":
        return "border-yellow-500 bg-yellow-950/30 text-yellow-300";
      case "info":
        return "border-blue-500 bg-blue-950/30 text-blue-300";
      case "recovery":
        return "border-green-500 bg-green-950/30 text-green-300";
      default:
        return "border-slate-700 bg-slate-800 text-slate-300";
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-white font-bold text-lg">
          Live SOC Alerts
        </h2>

        <span className="text-xs text-slate-400">
          realtime stream
        </span>
      </div>

      {/* Alert Stream */}
      <div className="space-y-3 overflow-y-auto h-[420px] pr-2">
        {alerts.length === 0 && (
          <div className="text-slate-500 text-sm">
            No active alerts
          </div>
        )}

        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`border rounded-md p-3 ${getAlertStyles(alert.type)}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold uppercase text-xs">
                {alert.type}
              </span>

              <span className="text-xs opacity-70">
                {alert.timestamp}
              </span>
            </div>

            <p className="mt-2 text-sm">
              {alert.message}
            </p>

            {alert.device && (
              <p className="mt-1 text-xs opacity-80">
                Device: {alert.device}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}