"use client";

export interface ThreatEvent {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  type: string;
  message: string;
  device?: string;
  timestamp: string;
  source?: string;
}

interface ThreatMonitorProps {
  threats: ThreatEvent[];
}

export default function ThreatMonitor({ threats }: ThreatMonitorProps) {
  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-500/20 text-red-400 border-red-500";
      case "high":
        return "bg-orange-500/20 text-orange-400 border-orange-500";
      case "medium":
        return "bg-yellow-500/20 text-yellow-300 border-yellow-500";
      case "low":
        return "bg-blue-500/20 text-blue-300 border-blue-500";
      default:
        return "bg-slate-700 text-slate-300";
    }
  };

  const getDot = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-500 animate-pulse";
      case "high":
        return "bg-orange-500";
      case "medium":
        return "bg-yellow-400";
      case "low":
        return "bg-blue-400";
      default:
        return "bg-slate-500";
    }
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 h-full">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-bold text-lg">
          Threat Intelligence Feed
        </h2>

        <span className="text-xs text-slate-500">
          live detection engine
        </span>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-4 gap-2 mb-4 text-xs">
        <div className="bg-red-500/10 p-2 rounded border border-red-500/30">
          Critical<br />
          <span className="text-red-400 font-bold">
            {threats.filter(t => t.severity === "critical").length}
          </span>
        </div>

        <div className="bg-orange-500/10 p-2 rounded border border-orange-500/30">
          High<br />
          <span className="text-orange-400 font-bold">
            {threats.filter(t => t.severity === "high").length}
          </span>
        </div>

        <div className="bg-yellow-500/10 p-2 rounded border border-yellow-500/30">
          Medium<br />
          <span className="text-yellow-300 font-bold">
            {threats.filter(t => t.severity === "medium").length}
          </span>
        </div>

        <div className="bg-blue-500/10 p-2 rounded border border-blue-500/30">
          Low<br />
          <span className="text-blue-300 font-bold">
            {threats.filter(t => t.severity === "low").length}
          </span>
        </div>
      </div>

      {/* Threat feed */}
      <div className="space-y-3 overflow-y-auto h-[420px] pr-2">
        {threats.length === 0 && (
          <div className="text-slate-500 text-sm">
            No threats detected
          </div>
        )}

        {threats.map((t) => (
          <div
            key={t.id}
            className={`
              border rounded-lg p-3
              ${getSeverityStyle(t.severity)}
            `}
          >
            <div className="flex items-start justify-between">
              
              {/* Left side */}
              <div className="flex items-start gap-2">
                <span className={`w-2 h-2 mt-2 rounded-full ${getDot(t.severity)}`} />
                
                <div>
                  <p className="text-sm font-semibold">
                    {t.type}
                  </p>

                  <p className="text-xs opacity-80">
                    {t.message}
                  </p>

                  {t.device && (
                    <p className="text-xs mt-1 opacity-60">
                      Device: {t.device}
                    </p>
                  )}
                </div>
              </div>

              {/* Right side */}
              <div className="text-xs opacity-60 text-right">
                {t.timestamp}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}