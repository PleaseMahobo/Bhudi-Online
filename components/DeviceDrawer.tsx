"use client";

interface Device {
  id: number;
  hostname: string;
  ip_address: string;
  status: string;
  cpu?: number;
  memory?: number;
  disk?: number;
  os?: string;
  last_seen?: string;
  site?: string;
}

interface DeviceDrawerProps {
  device: Device | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function DeviceDrawer({
  device,
  isOpen,
  onClose,
}: DeviceDrawerProps) {
  if (!device) return null;

  return (
    <div
      className={`
        fixed top-0 right-0 h-full w-[420px]
        bg-slate-900 border-l border-slate-700
        shadow-2xl z-50
        transform transition-transform duration-300
        ${isOpen ? "translate-x-0" : "translate-x-full"}
      `}
    >
      <div className="flex items-center justify-between p-5 border-b border-slate-700">
        <h2 className="text-xl font-bold text-white">
          {device.hostname}
        </h2>

        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="p-5 space-y-4 text-sm">
        <InfoRow label="Hostname" value={device.hostname} />
        <InfoRow label="IP Address" value={device.ip_address} />
        <InfoRow label="Operating System" value={device.os || "Unknown"} />
        <InfoRow label="Site" value={device.site || "Unknown"} />

        <InfoRow
          label="Last Heartbeat"
          value={device.last_seen || "Unknown"}
        />

        <div className="pt-4 border-t border-slate-700">
          <h3 className="text-white font-semibold mb-4">
            Device Health
          </h3>

          <MetricBar
            label="CPU"
            value={device.cpu || 0}
          />

          <MetricBar
            label="Memory"
            value={device.memory || 0}
          />

          <MetricBar
            label="Disk"
            value={device.disk || 0}
          />
        </div>

        <div className="pt-4 border-t border-slate-700">
          <h3 className="text-white font-semibold mb-3">
            Status
          </h3>

          <div
            className={`
              inline-flex px-3 py-1 rounded-full text-sm
              ${
                device.status === "online"
                  ? "bg-green-500/20 text-green-400"
                  : "bg-red-500/20 text-red-400"
              }
            `}
          >
            {device.status.toUpperCase()}
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-slate-400">{label}</p>
      <p className="text-white">{value}</p>
    </div>
  );
}

function MetricBar({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="mb-4">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-300">{label}</span>
        <span className="text-white">{value}%</span>
      </div>

      <div className="h-2 bg-slate-700 rounded">
        <div
          className="h-2 bg-cyan-500 rounded"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}