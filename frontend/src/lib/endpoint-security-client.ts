// frontend/src/lib/endpoint-security-client.ts
// Cloud sync + provider helpers for Endpoint Security UI

const API_BASE = "";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message =
        typeof body?.detail === "string"
          ? body.detail
          : body?.message ?? body?.error ?? JSON.stringify(body);
    } catch {}
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

function qs(params?: Record<string, string | number | boolean | undefined | null>) {
  if (!params) return "";
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  const value = sp.toString();
  return value ? `?${value}` : "";
}

const ES = "/api/v1/endpoint-security";

export async function listSecurityProviders() {
  return request<any[]>(`${ES}/providers`);
}
export async function seedSecurityProviders(tenantId?: string | null) {
  const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  return request<any[]>(`${ES}/providers/seed${q}`, { method: "POST" });
}
export async function updateSecurityProvider(id: string, data: Record<string, unknown>) {
  return request<any>(`${ES}/providers/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function syncSecurityProvider(id: string) {
  return request<any>(`${ES}/providers/${id}/sync`, { method: "POST" });
}
export async function syncAllSecurityProviders(tenantId?: string | null) {
  const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  return request<{ results: any[] }>(`${ES}/providers/sync-all${q}`, { method: "POST" });
}
export async function listSecurityConnectors() {
  return request<{ connectors: string[]; note?: string }>(`${ES}/connectors`);
}
export async function listSecurityAgents(params?: { provider_id?: string; device_id?: string }) {
  return request<any[]>(`${ES}/agents${qs(params as any)}`);
}
export async function createSecurityAgent(data: Record<string, unknown>) {
  return request<any>(`${ES}/agents`, { method: "POST", body: JSON.stringify(data) });
}
export async function listSecurityFindings(params?: {
  status?: string;
  severity?: string;
  provider_id?: string;
  device_id?: string;
}) {
  return request<any[]>(`${ES}/findings${qs(params as any)}`);
}
export async function createSecurityFinding(data: Record<string, unknown>) {
  return request<any>(`${ES}/findings`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateSecurityFinding(id: string, data: Record<string, unknown>) {
  return request<any>(`${ES}/findings/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function getOrgSecurityScore() {
  return request<any>(`${ES}/scores/org`);
}
export async function listSecurityScores(minScore?: number) {
  const q = minScore != null ? `?min_score=${minScore}` : "";
  return request<any[]>(`${ES}/scores${q}`);
}
export async function recomputeAllSecurityScores() {
  return request<{ devices_scored: number }>(`${ES}/scores/recompute-all`, { method: "POST" });
}
export async function getSecurityMatrix(params?: { device_id?: string; hostname?: string }) {
  return request<any>(`${ES}/matrix${qs(params as any)}`);
}
