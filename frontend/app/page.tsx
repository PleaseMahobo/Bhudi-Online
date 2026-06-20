"use client";

import { useEffect, useState } from "react";

const API_URL = "https://bhudi-online-production.up.railway.app";

export default function Home() {
  const [devices, setDevices] = useState([]);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    loadData();

    const interval = setInterval(() => {
      loadData();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      const [healthRes, devicesRes] = await Promise.all([
        fetch(`${API_URL}/health`),
        fetch(`${API_URL}/devices`)
      ]);

      const healthData = await healthRes.json();
      const devicesData = await devicesRes.json();

      setHealth(healthData);
      setDevices(devicesData.devices || []);
    } catch (err) {
      console.error("Dashboard error:", err);
    }
  }

  return (
    <div style={{ padding: 20, fontFamily: "Arial" }}>
      <h1>Bhudi RMM Dashboard</h1>

      <div style={{ marginBottom: 20 }}>
        <strong>Backend Status:</strong>
        <pre>{JSON.stringify(health, null, 2)}</pre>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h2>Devices ({devices.length})</h2>

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
    </div>
  );
}