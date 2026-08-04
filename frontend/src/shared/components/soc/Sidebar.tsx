export default function Sidebar() {
  return (
    <div className="w-64 bg-[#0f1629] border-r border-gray-800 p-4">
      <h1 className="text-xl font-bold mb-6">Bhudi RMM</h1>

      <nav className="space-y-3 text-sm">
        <div className="text-blue-400 font-semibold">Dashboard</div>
        <div className="text-gray-400">Devices</div>
        <div className="text-gray-400">Commands</div>
        <div className="text-gray-400">Alerts</div>
        <div className="text-gray-400">Logs</div>
        <div className="text-gray-400">Settings</div>
      </nav>
    </div>
  );
}