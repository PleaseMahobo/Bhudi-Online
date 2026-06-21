// frontend/lib/api.ts
const envApiUrl = typeof globalThis !== 'undefined' && 'process' in globalThis
  ? (globalThis as any).process?.env?.NEXT_PUBLIC_API_URL
  : undefined;
const API_BASE = envApiUrl || "https://bhudi-online-production.up.railway.app";

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`, {
    cache: 'no-store',
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function getDeviceStatus() {
  const res = await fetch(`${API_BASE}/devices/status`, {
    cache: 'no-store',
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) return { devices: [] };
  return res.json();
}