const BASE_URL = "http://localhost:8000";

export async function getDevices() {
  const res = await fetch(`${BASE_URL}/devices`);
  return res.json();
}

export async function sendCommand(device_id: number, command: string) {
  const res = await fetch(`${BASE_URL}/commands`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_id, command }),
  });

  return res.json();
}