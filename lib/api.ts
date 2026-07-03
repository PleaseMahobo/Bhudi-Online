// frontend/lib/api.ts
declare const process: { env: { NEXT_PUBLIC_API_URL?: string } };
const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://bhudi-online-production.up.railway.app";

export async function getHealth() {
  try {
    const res = await fetch(`${API_URL}/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });
    if (!res.ok) return { status: "error", message: `HTTP ${res.status}` };
    return await res.json();
  } catch (error) {
    console.error("Health check failed:", error);
    return { status: "error", message: "Backend unreachable" };
  }
}

export async function getDeviceStatus() {
  try {
    const res = await fetch(`${API_URL}/devices/status`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });
    if (!res.ok) return { devices: [] };
    return await res.json();
  } catch (error) {
    console.error("Device status failed:", error);
    return { devices: [] };
  }
}