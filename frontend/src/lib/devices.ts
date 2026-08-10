/** Phase 1 unified devices client (Tactical-style status model). */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

export type DeviceStatus = 'online' | 'offline' | 'overdue' | 'unknown' | string;

export interface Device {
  id: string;
  device_id?: string;
  agent_id?: string;
  hostname?: string;
  name?: string;
  status?: DeviceStatus;
  online?: boolean;
  last_seen?: string;
  platform?: string;
  agent_version?: string;
  ip_address?: string;
  cpu_percent?: number | null;
  memory_percent?: number | null;
  disk_percent?: number | null;
  source?: string;
}

export interface DevicesListResponse {
  devices: Device[];
  count: number;
  counts?: Record<string, number>;
}

function normalizeDevice(raw: any): Device {
  return {
    id: String(raw?.id ?? raw?.device_id ?? raw?.agent_id ?? ''),
    device_id: raw?.device_id ?? raw?.agent_id,
    agent_id: raw?.agent_id ?? raw?.device_id,
    hostname: raw?.hostname,
    name: raw?.name,
    status: raw?.status,
    online: raw?.online ?? String(raw?.status || '').toLowerCase() === 'online',
    last_seen:
      typeof raw?.last_seen === 'string'
        ? raw.last_seen
        : raw?.last_seen?.toString?.(),
    platform: raw?.platform,
    agent_version: raw?.agent_version ?? raw?.version,
    ip_address: raw?.ip_address ?? raw?.ip,
    cpu_percent: raw?.cpu_percent ?? null,
    memory_percent: raw?.memory_percent ?? null,
    disk_percent: raw?.disk_percent ?? null,
    source: raw?.source,
  };
}

export async function listDevicesDetailed(): Promise<DevicesListResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = getAccessToken();
  if (token) headers.Authorization = 'Bearer ' + token;

  const response = await fetch(API_BASE + '/api/v1/devices/', { headers });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  const payload = await response.json();
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.devices)
      ? payload.devices
      : [];
  const devices = list.map(normalizeDevice);
  return {
    devices,
    count: payload?.count ?? devices.length,
    counts: payload?.counts || {},
  };
}
