"use client";

export interface SiteNode {
  id: string;
  name: string;
  status: "online" | "degraded" | "offline";
  devices: number;
}

interface TopologyMapProps {
  sites: SiteNode[];
}

export default function TopologyMap({ sites }: TopologyMapProps) {
  const getColor = (status: string) => {
    switch (status) {
      case "online":
        return "bg-green-500";
      case "degraded":
        return "bg-yellow-500";
      case "offline":
        return "bg-red-500 animate-pulse";
      default:
        return "bg-slate-500";
    }
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 h-full">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-bold text-lg">
          Network Topology
        </h2>

        <span className="text-xs text-slate-500">
          live site map
        </span>
      </div>

      {/* Core topology layout */}
      <div className="relative flex flex-col items-center gap-6">

        {/* Core node */}
        <div className="text-center">
          <div className="w-4 h-4 bg-cyan-400 rounded-full mx-auto animate-pulse"></div>
          <p className="text-xs text-slate-300 mt-1">SOC CORE</p>
        </div>

        {/* Branch lines */}
        <div className="w-px h-6 bg-slate-700"></div>

        {/* Sites */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full">
          {sites.map((site) => (
            <div
              key={site.id}
              className="
                bg-slate-900
                border border-slate-800
                rounded-lg
                p-3
                text-center
                hover:border-cyan-500
                transition
              "
            >
              {/* Status dot */}
              <div
                className={`w-3 h-3 rounded-full mx-auto mb-2 ${getColor(
                  site.status
                )}`}
              />

              {/* Site name */}
              <p className="text-white text-sm font-semibold">
                {site.name}
              </p>

              {/* Device count */}
              <p className="text-xs text-slate-400 mt-1">
                {site.devices} devices
              </p>

              {/* Status label */}
              <p className="text-xs mt-2 text-slate-500 capitalize">
                {site.status}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}