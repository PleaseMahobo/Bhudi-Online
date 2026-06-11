const API_URL =
process.env.NEXT_PUBLIC_API_URL ||
"https://ubiquitous-space-potato-v6jq74wpxw4w3pwpj-8000.app.github.dev";

export async function getHealth() {
const res = await fetch(`${API_URL}/health`);

if (!res.ok) {
throw new Error("Health check failed");
}

return res.json();
}

export async function sendHeartbeat(deviceId: string) {
const res = await fetch(`${API_URL}/heartbeat/${deviceId}`, {
method: "POST",
});

if (!res.ok) {
throw new Error("Heartbeat failed");
}

return res.json();
}

export async function getDeviceStatus() {
const res = await fetch(`${API_URL}/devices/status`);

if (!res.ok) {
throw new Error("Device status fetch failed");
}

return res.json();
}
