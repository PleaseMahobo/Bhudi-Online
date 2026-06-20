"use client";

import { useEffect, useState } from "react";
import { getHealth } from "../lib/api";

export default function Home() {
  const [status, setStatus] = useState("loading...");

  useEffect(() => {
    async function run() {
      try {
        const data = await getHealth();

          setStatus(
            JSON.stringify({
              apiUrl: process.env.NEXT_PUBLIC_API_URL,
              response: data,
            })
          );
      } catch (err) {
        setStatus(`ERROR: ${err?.message || String(err)}`);
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