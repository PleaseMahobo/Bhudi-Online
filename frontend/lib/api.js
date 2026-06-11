const BASE_URL = "https://ubiquitous-space-potato-v6jq74wpxw4w3pwpj-8000.app.github.dev";

export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}