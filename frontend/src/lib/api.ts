// frontend/src/lib/api.ts

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function setAccessToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem("access_token", token);
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function setRefreshToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem("refresh_token", token);
}

function clearTokens() {
  if (typeof window === "undefined") return;

  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {

  const headers = new Headers(options.headers);

  headers.set("Content-Type", "application/json");

  const token = getAccessToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(
    `${API_BASE}${endpoint}`,
    {
      ...options,
      headers,
    }
  );

  if (!response.ok) {

    let message = response.statusText;

    try {
      const body = await response.json();
      message = body.detail ?? JSON.stringify(body);
    } catch {}

    throw new Error(message);
  }

  return response.json();
}

export interface User {

  id: string;

  email: string;

  first_name: string;

  last_name: string;

  role: string;

  active: boolean;
}

export interface LoginResponse {

  access_token: string;

  refresh_token: string;

  token_type: string;

  user: User;
}

export interface Device {

  id: string;

  device_id?: string;

  hostname?: string;

  name?: string;

  status?: string;

  online?: boolean;

  last_seen?: string;
}

function normalizeDevice(raw: any): Device {
  return {
    id: String(raw?.id ?? raw?.device_id ?? ""),
    device_id: raw?.device_id,
    hostname: raw?.hostname,
    name: raw?.name,
    status: raw?.status,
    online: raw?.online,
    last_seen: raw?.last_seen,
  };
}

function normalizeDevicesPayload(payload: any): Device[] {
  if (Array.isArray(payload)) {
    return payload.map(normalizeDevice);
  }

  if (payload && Array.isArray(payload.devices)) {
    return payload.devices.map(normalizeDevice);
  }

  return [];
}

export interface HealthResponse {

  status: string;

  service?: string;

  version?: string;

  message?: string;
}

export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {

  const result = await request<LoginResponse>(
    "/api/v1/auth/login",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
      }),
    }
  );

  setAccessToken(result.access_token);
  setRefreshToken(result.refresh_token);

  return result;
}

export async function logout() {

  try {

    await request(
      "/api/v1/auth/logout",
      {
        method: "POST",
      }
    );

  } finally {

    clearTokens();

  }

}

export async function getCurrentUser() {

  return request<User>(
    "/api/v1/auth/me"
  );

}

export async function refreshAccessToken() {

  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    throw new Error("No refresh token");
  }

  const result = await request<LoginResponse>(
    "/api/v1/auth/refresh",
    {
      method: "POST",
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    }
  );

  setAccessToken(result.access_token);
  setRefreshToken(result.refresh_token);

  return result;
}

export async function getHealth() {

  return request<HealthResponse>(
    "/health"
  );

}

export async function getDevices() {
  const payload = await request<any>(
    "/api/v1/devices/"
  );

  return normalizeDevicesPayload(payload);

}

/*
Temporary compatibility wrapper.

The dashboard still calls getDeviceStatus().

When we modernize the dashboard we can remove this.
*/

export async function getDeviceStatus() {
  return getDevices();

}