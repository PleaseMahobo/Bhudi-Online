// Asset management clients — re-exported via api-modules / api.ts
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

export async function listAssets(params?: { status?: string; device_id?: string; tenant_id?: string }) {
  return request<any[]>(`/api/v1/assets${qs(params as any)}`);
}
export async function createAsset(data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateAsset(id: string, data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function deleteAsset(id: string) {
  return request<void>(`/api/v1/assets/${id}`, { method: "DELETE" });
}
export async function changeAssetStatus(id: string, status: string, reason?: string) {
  return request<any>(`/api/v1/assets/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ status, reason }),
  });
}
export async function ensureAssetQr(id: string) {
  return request<{ asset_id: string; qr_code: string }>(`/api/v1/assets/${id}/qr`, { method: "POST" });
}
export async function getAssetWarranty(id: string) {
  return request<any>(`/api/v1/assets/${id}/warranty`);
}
export async function getAssetDepreciation(id: string) {
  return request<any>(`/api/v1/assets/${id}/depreciation`);
}
export async function listAssetLifecycle(id: string) {
  return request<any[]>(`/api/v1/assets/${id}/lifecycle`);
}
export async function listVendors(activeOnly = false) {
  return request<any[]>(`/api/v1/assets/vendors${activeOnly ? "?active_only=true" : ""}`);
}
export async function createVendor(data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets/vendors`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateVendor(id: string, data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets/vendors/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function deleteVendor(id: string) {
  return request<void>(`/api/v1/assets/vendors/${id}`, { method: "DELETE" });
}
export async function listLicenses() {
  return request<any[]>(`/api/v1/assets/licenses`);
}
export async function createLicense(data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets/licenses`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateLicense(id: string, data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets/licenses/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function deleteLicense(id: string) {
  return request<void>(`/api/v1/assets/licenses/${id}`, { method: "DELETE" });
}
export async function listContracts() {
  return request<any[]>(`/api/v1/assets/contracts`);
}
export async function createContract(data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets/contracts`, { method: "POST", body: JSON.stringify(data) });
}
export async function updateContract(id: string, data: Record<string, unknown>) {
  return request<any>(`/api/v1/assets/contracts/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}
export async function deleteContract(id: string) {
  return request<void>(`/api/v1/assets/contracts/${id}`, { method: "DELETE" });
}
