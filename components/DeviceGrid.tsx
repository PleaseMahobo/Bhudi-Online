"use client";

import React from "react";

export default function DeviceGrid({ devices }: any) {
  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      {Object.values(devices).map((d: any) => (
        <div
          key={d.device_id}
          className={`p-4 rounded-xl shadow border ${
            d.status === "online" ? "bg-green-50" : "bg-red-50"
          } cursor-pointer hover:shadow-lg transition`}
        >
          <h3 className="font-bold">{d.device_id}</h3>
          <p>Status: {d.status}</p>
          <p className="text-sm text-gray-500">{d.last_seen}</p>
        </div>
      ))}
    </div>
  );
}