"use client";

import { useState } from "react";

export interface Node {
  id: string;
  type: "core" | "site" | "device";
  name: string;
  status: "online" | "degraded" | "offline";
  parentId?: string;
}

interface TopologyMapV2Props {
  nodes: Node[];
  onSelectNode?: (node: Node) => void;
}

export default function TopologyMapV2({
  nodes,
  onSelectNode,
}: TopologyMapV2Props) {
  const [selected, setSelected] = useState<Node | null>(null);

  const handleSelect = (node: Node) => {
    setSelected(node);
    onSelectNode?.(node);
  };

  const getColor = (status: Node["status"]) => {
    switch (status) {
      case "online":
        return "bg-green-500";
      case "degraded":
        return "bg-yellow-500 animate-pulse";
      case "offline":
        return "bg-red-500 animate-pulse";
    }
  };

  const core = nodes.find(n => n.type === "core");
  const sites = nodes.filter(n => n.type === "site");
  const devices = nodes.filter(n => n.type === "device");

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 h-full overflow-auto">

      {/* HEADER */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-white font-bold text-lg">
          Live Infrastructure Topology
        </h2>

        <span className="text-xs text-slate-500">
          interactive SOC graph
        </span>
      </div>

      {/* CORE NODE */}
      {core && (
        <div className="flex flex-col items-center mb-6">
          <div
            onClick={() => handleSelect(core)}
            className="cursor-pointer text-center"
          >
            <div className="w-5 h-5 bg-cyan-400 rounded-full mx-auto animate-pulse" />
            <p className="text-xs text-slate-300 mt-1">
              {core.name}
            </p>
          </div>

          <div className="w-px h-6 bg-slate-700 mt-2" />
        </div>
      )}

      {/* SITE LAYER */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {sites.map(site => (
          <div key={site.id} className="flex flex-col items-center">

            <div
              onClick={() => handleSelect(site)}
              className="cursor-pointer bg-slate-900 border border-slate-800 hover:border-cyan-500 rounded-lg p-3 w-full text-center transition"
            >
              <div className={`w-3 h-3 rounded-full mx-auto mb-2 ${getColor(site.status)}`} />
              <p className="text-white text-sm">{site.name}</p>
            </div>

            {/* CONNECTOR LINE */}
            <div className="w-px h-4 bg-slate-700" />

            {/* DEVICE LAYER */}
            <div className="space-y-2 w-full">
              {devices
                .filter(d => d.parentId === site.id)
                .map(device => (
                  <div
                    key={device.id}
                    onClick={() => handleSelect(device)}
                    className="
                      cursor-pointer
                      bg-slate-800
                      border border-slate-700
                      hover:border-cyan-500
                      rounded-md
                      p-2
                      text-center
                      text-xs
                      text-slate-300
                    "
                  >
                    <div className={`w-2 h-2 mx-auto mb-1 rounded-full ${getColor(device.status)}`} />
                    {device.name}
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>

      {/* DETAIL PANEL */}
      {selected && (
        <div className="mt-4 border-t border-slate-800 pt-3">
          <p className="text-white text-sm font-semibold">
            Selected Node
          </p>

          <div className="text-xs text-slate-400 mt-1">
            {selected.name} • {selected.type.toUpperCase()} • {selected.status.toUpperCase()}
          </div>
        </div>
      )}
    </div>
  );
}