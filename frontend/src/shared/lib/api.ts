const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://bhudi-online-production.up.railway.app";

export async function getHealth() {
  const res = await fetch(`${API_URL}/health`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store'
  });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function getDeviceStatus() {
  const res = await fetch(`${API_URL}/devices/status`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store'
  });
  if (!res.ok) return { devices: [] };
  return res.json();
}