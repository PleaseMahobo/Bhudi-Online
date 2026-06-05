export default function DevicePanel({ devices }: any) {
  return (
    <div>
      <h2 className="text-lg mb-4">Device Fleet</h2>

      <div className="grid grid-cols-2 gap-3">
        {devices?.map((d: any) => (
          <div
            key={d.id}
            className="p-3 rounded bg-[#111827] border border-gray-800"
          >

            <div className="flex justify-between">
              <span className="font-medium">{d.hostname}</span>

              <span
                className={
                  d.status === "online"
                    ? "text-green-400"
                    : "text-red-400"
                }
              >
                ●
              </span>
            </div>

            <div className="text-xs text-gray-400 mt-1">
              {d.ip_address}
            </div>

          </div>
        ))}
      </div>
    </div>
  );
}