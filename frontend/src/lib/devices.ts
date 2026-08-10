/** Phase 1–2 unified devices client (Tactical-style). */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

function headers(): HeadersInit {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = getAccessToken();
  if (token) h.Authorization = 'Bearer ' + token;
  return h;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, {
    ...init,
    headers: { ...headers(), ...(init?.headers || {}) },
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
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
  organization_id?: string;
  organization_name?: string;
  site_id?: string;
  site_name?: string;
}

export interface DevicesListResponse {
  devices: Device[];
  count: number;
  counts?: Record<string, number>;
}

export interface OrgNode {
  id: string;
  name: string;
  sites?: { id: string; name: string; organization_id?: string }[];
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
      typeof raw?.last_seen === 'string' ? raw.last_seen : raw?.last_seen?.toString?.(),
    platform: raw?.platform,
    agent_version: raw?.agent_version ?? raw?.version,
    ip_address: raw?.ip_address ?? raw?.ip,
    cpu_percent: raw?.cpu_percent ?? null,
    memory_percent: raw?.memory_percent ?? null,
    disk_percent: raw?.disk_percent ?? null,
    source: raw?.source,
    organization_id: raw?.organization_id ? String(raw.organization_id) : undefined,
    organization_name: raw?.organization_name,
    site_id: raw?.site_id ? String(raw.site_id) : undefined,
    site_name: raw?.site_name,
  };
}

export async function listDevicesDetailed(): Promise<DevicesListResponse> {
  const payload = await api<any>('/api/v1/devices/');
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

export async function getDevice(id: string): Promise<Device> {
  const raw = await api<any>('/api/v1/devices/' + encodeURIComponent(id));
  return normalizeDevice(raw);
}

export async function requestInventory(deviceId: string, kind: 'processes' | 'software') {
  return api<{ accepted: boolean; command_id: string; kind: string; command: string }>(
    '/api/v1/devices/' + encodeURIComponent(deviceId) + '/inventory/' + kind,
    { method: 'POST' }
  );
}

export async function getDeviceCommand(deviceId: string, commandId: string) {
  return api<{
    command_id: string;
    status: string;
    command?: string;
    result?: { exit_code?: number; stdout?: string; stderr?: string };
    finished_at?: string;
  }>(
    '/api/v1/devices/' +
      encodeURIComponent(deviceId) +
      '/commands/' +
      encodeURIComponent(commandId)
  );
}

export async function waitForCommand(
  deviceId: string,
  commandId: string,
  timeoutMs = 45000
): Promise<{ exit_code?: number; stdout?: string; stderr?: string; status: string }> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const row = await getDeviceCommand(deviceId, commandId);
    if (row.status === 'completed' || row.result) {
      return { ...(row.result || {}), status: row.status };
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error('Timed out waiting for agent inventory result');
}

export async function listOrganizations(): Promise<OrgNode[]> {
  try {
    const orgs = await api<any[]>('/api/v1/msp/organizations');
    const sites = await api<any[]>('/api/v1/msp/sites').catch(() => []);
    return (orgs || []).map((o) => ({
      id: String(o.id),
      name: o.name || o.display_name || 'Organization',
      sites: (sites || [])
        .filter((s) => String(s.organization_id) === String(o.id))
        .map((s) => ({
          id: String(s.id),
          name: s.name || 'Site',
          organization_id: String(s.organization_id),
        })),
    }));
  } catch {
    return [];
  }
}

export function remoteDeepLink(agentId: string, mode: 'desktop' | 'terminal' = 'desktop') {
  return '/remote?agent=' + encodeURIComponent(agentId) + '&mode=' + mode;
}

export function deviceDetailPath(id: string, tab?: string) {
  const base = '/devices/' + encodeURIComponent(id);
  return tab ? base + '?tab=' + encodeURIComponent(tab) : base;
}
