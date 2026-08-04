"use client";

interface Props {
  activeNodes: string[];
}

export default function LiveHeartbeatOverlay({ activeNodes }: Props) {
  return (
    <div className="absolute inset-0 pointer-events-none">
      {activeNodes.map((id) => (
        <div
          key={id}
          className="absolute w-2 h-2 bg-cyan-400 rounded-full animate-ping opacity-70"
          style={{
            top: `${Math.random() * 80 + 10}%`,
            left: `${Math.random() * 80 + 10}%`,
          }}
        />
      ))}
    </div>
  );
}