/** Phase 1–2 unified devices client (Tactical-style). */

const API_BASE = '';

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type') && init?.body) headers.set('Content-Type', 'application/json');
  headers.set('Accept', 'application/json');
  const response = await fetch(API_BASE + path, { ...init, headers, credentials: 'include', cache: 'no-store' });
  if (!response.ok) {
    let message = response.statusText;
    try { const body = await response.json(); message = body.detail ?? body.message ?? JSON.stringify(body); } catch {}
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export type DeviceStatus = 'online' | 'offline' | 'overdue' | 'unknown' | string;
export type HealthGrade = 'A' | 'B' | 'C' | 'D' | 'F' | string;

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
  temperature_c?: number | null;
  smart_status?: string | null;
  health_score?: number | null;
  health_grade?: HealthGrade | null;
  consecutive_misses?: number | null;
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

function gradeFromScore(score?: number | null): HealthGrade | null {
  if (score == null || Number.isNaN(Number(score))) return null;
  const s = Number(score);
  if (s >= 90) return 'A';
  if (s >= 80) return 'B';
  if (s >= 70) return 'C';
  if (s >= 60) return 'D';
  return 'F';
}

function normalizeDevice(raw: any): Device {
  const health_score =
    raw?.health_score != null ? Number(raw.health_score) : null;
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
    temperature_c: raw?.temperature_c ?? null,
    smart_status: raw?.smart_status ?? null,
    health_score,
    health_grade: raw?.health_grade ?? gradeFromScore(health_score),
    consecutive_misses: raw?.consecutive_misses ?? null,
    source: raw?.source,
    organization_id: raw?.organization_id
      ? String(raw.organization_id)
      : undefined,
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
  return normalizeDevice(
    await api<any>('/api/v1/devices/' + encodeURIComponent(id))
  );
}

export async function requestInventory(
  deviceId: string,
  kind: 'processes' | 'software'
) {
  return api<{
    accepted: boolean;
    command_id: string;
    kind: string;
    command: string;
  }>(
    '/api/v1/devices/' +
      encodeURIComponent(deviceId) +
      '/inventory/' +
      kind,
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
): Promise<{
  exit_code?: number;
  stdout?: string;
  stderr?: string;
  status: string;
}> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const row = await getDeviceCommand(deviceId, commandId);
    if (row.status === 'completed' || row.result)
      return { ...(row.result || {}), status: row.status };
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

export function remoteDeepLink(
  agentId: string,
  mode: 'desktop' | 'terminal' = 'desktop'
) {
  return (
    '/remote?agent=' + encodeURIComponent(agentId) + '&mode=' + mode
  );
}

export function deviceDetailPath(id: string, tab?: string) {
  const base = '/devices/' + encodeURIComponent(id);
  return tab ? base + '?tab=' + encodeURIComponent(tab) : base;
}

/** CSS classes for health grade badge */
export function healthGradeClass(grade?: string | null): string {
  const g = (grade || '').toUpperCase();
  if (g === 'A') return 'bg-emerald-50 text-emerald-800 border-emerald-200';
  if (g === 'B') return 'bg-lime-50 text-lime-800 border-lime-200';
  if (g === 'C') return 'bg-amber-50 text-amber-900 border-amber-200';
  if (g === 'D') return 'bg-orange-50 text-orange-900 border-orange-200';
  if (g === 'F') return 'bg-red-50 text-red-800 border-red-200';
  return 'bg-slate-50 text-slate-600 border-slate-200';
}
