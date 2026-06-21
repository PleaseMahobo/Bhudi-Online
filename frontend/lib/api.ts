// frontend/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://bhudi-online-production.up.railway.app";

export const api = {
  async getHealth() {
    const res = await fetch(`${API_URL}/health`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Health check failed");
    return res.json();
  },

  async getDevices() {
    const res = await fetch(`${API_URL}/devices/status`, { cache: 'no-store' });
    if (!res.ok) return { devices: [] };
    return res.json();
  },

  async sendCommand(deviceId: string | number, command: string) {
    const res = await fetch(`${API_URL}/commands/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId, command }),
    });
    if (!res.ok) throw new Error("Command failed");
    return res.json();
  }
};