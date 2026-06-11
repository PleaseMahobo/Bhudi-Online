"use client";

import { useEffect, useState } from "react";
import { getHealth } from "../lib/api";

export default function Home() {
  const [status, setStatus] = useState("loading...");

  useEffect(() => {
    async function run() {
      try {
        const data = await getHealth();
        setStatus(JSON.stringify(data));
      } catch (err) {
        setStatus("Backend not reachable");
      }
    }

    run();
  }, []);

  return (
    <div style={{ padding: 20 }}>
      <h1>Bhudi RMM Dashboard</h1>

      <p>Backend Status:</p>

      <pre>{status}</pre>
    </div>
  );
}