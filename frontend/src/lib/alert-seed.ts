import type { AlertRule, EscalationPolicy } from './api';

// Thin client for alert-engine seed-defaults so api.ts stays smaller for deploys.

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json');
  headers.set('Accept', 'application/json');
  const response = await fetch(endpoint, { ...options, headers, credentials: 'include', cache: 'no-store' });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      const detail = body?.detail;
      message = typeof detail === 'string' ? detail : body?.message ?? body?.error ?? JSON.stringify(body);
    } catch {}
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export type SeedAlertDefaultsResponse = {
  created: number;
  skipped?: number;
  message: string;
  rules?: AlertRule[];
  policies?: EscalationPolicy[];
  defaults?: string[];
};

export async function seedAlertDefaults(force = false) {
  const q = force ? '?force=true' : '';
  return request<SeedAlertDefaultsResponse>(`/api/v1/alert-engine/seed-defaults${q}`, { method: 'POST' });
}
