// frontend/src/lib/api.ts

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "https://bhudi-online-production.up.railway.app";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(
      `API request failed (${response.status}) ${response.statusText}`
    );
  }

  return response.json();
}

export interface Device {
  id: number;
  name: string;
  status: string;
  [key: string]: any;
}

export interface DeviceStatusResponse {
  devices: Device[];
}

export interface HealthResponse {
    status: string;
    message?: string;
}

export function getHealth() {
    return request<HealthResponse>("/health");
}

export async function getDeviceStatus(): Promise<Device[]> {
  const response = await request<DeviceStatusResponse>("/devices/status");
  return response.devices;
}

export function sendCommand(
  deviceId: number,
  command: string
) {
  return request("/commands", {
    method: "POST",
    body: JSON.stringify({
      device_id: deviceId,
      command,
    }),
  });
}

export function login(
  email: string,
  password: string
) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
    }),
  });
}

export function logout() {
  return request("/api/auth/logout", {
    method: "POST",
  });
}

export function getCurrentUser() {
  return request("/api/auth/me");
}

export function refreshToken() {
  return request("/api/auth/refresh", {
    method: "POST",
  });
}