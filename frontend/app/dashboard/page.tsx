"use client";

import { useEffect, useState } from "react";

const API = "https://bhudi-online-production.up.railway.app";

export default function Dashboard() {
  const [devices, setDevices] = useState([]);
  const [health, setHealth] = useState(null);

  async function load() {
    try {
      const [hRes, dRes] = await Promise.all([
        fetch(`${API}/health`),
        fetch(`${API}/devices`)
      ]);

      const hData = await hRes.json();
      const dData = await dRes.json();

      setHealth(hData);
      setDevices(dData.devices || []);
    } catch (err) {
      console.error("Dashboard error:", err);
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: 20, fontFamily: "Arial" }}>
      <h1>RMM Dashboard</h1>

      <h3>Backend Status</h3>
      <pre>{JSON.stringify(health, null, 2)}</pre>

      <h3>Devices ({devices.length})</h3>

      {devices.length === 0 ? (
        <p>No devices connected</p>
      ) : (
        <table border="1" cellPadding="8">
          <thead>
            <tr>
              <th>Device ID</th>
              <th>Status</th>
              <th>Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((d: any, i) => (
              <tr key={i}>
                <td>{d.device_id}</td>
                <td>{d.status}</td>
                <td>{d.last_seen}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}