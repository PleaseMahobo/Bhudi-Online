export default function TopBar({ onlineCount, devices }: any) {
  const total = devices?.length || 0;

  return (
    <div className="h-12 flex items-center justify-between px-4 border-b border-gray-800 bg-[#0f1629]">

      <div className="text-sm text-gray-300">
        SOC Operations Center
      </div>

      <div className="flex gap-6 text-sm">
        <span className="text-green-400">
          Online: {onlineCount}
        </span>

        <span className="text-gray-400">
          Total: {total}
        </span>
      </div>

    </div>
  );
}