"use client";

export interface CommandEvent {
  id: string;
  device: string;
  command: string;
  status: "success" | "failed" | "pending";
  timestamp: string;
  user?: string;
}

interface Props {
  events: CommandEvent[];
}

export default function CommandTimeline({ events }: Props) {
  const statusColor = (status: string) => {
    switch (status) {
      case "success":
        return "text-green-400";
      case "failed":
        return "text-red-400";
      case "pending":
        return "text-yellow-400";
    }
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 h-full">
      <h2 className="text-white font-bold mb-4">
        Command Execution Timeline
      </h2>

      <div className="space-y-3 overflow-y-auto h-[420px]">
        {events.map((e) => (
          <div
            key={e.id}
            className="border border-slate-800 p-3 rounded bg-slate-900"
          >
            <div className="flex justify-between">
              <p className="text-white text-sm">{e.command}</p>
              <p className={`text-xs ${statusColor(e.status)}`}>
                {e.status.toUpperCase()}
              </p>
            </div>

            <div className="text-xs text-slate-400 mt-1">
              {e.device} • {e.timestamp}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}