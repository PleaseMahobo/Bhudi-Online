const BASE_URL = "https://ubiquitous-space-potato-v6jq74wpxw4w3pwpj-8000.app.github.dev";

export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);

  if (!res.ok) {
    throw new Error("Health check failed");
  }

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