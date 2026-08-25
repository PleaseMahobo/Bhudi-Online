// Alert Engine active-alert helpers (keeps api.ts lean)

const API_BASE = '';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json');
  headers.set('Accept', 'application/json');
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = typeof body?.detail === 'string' ? body.detail : body?.message || message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export type ActiveAlert = {
  id: string;
  provider: string;
  alert_type: string;
  severity: string;
  message: string;
  suppressed?: boolean;
  suppression_reason?: string | null;
  escalation_level?: number;
  correlated_count?: number;
  resolved?: boolean;
  acknowledged?: boolean;
  fingerprint?: string | null;
  correlation_key?: string | null;
  context?: Record<string, unknown> | null;
  created_at?: string | null;
};

export async function listActiveAlerts(opts?: { resolved?: boolean; limit?: number }) {
  const q = new URLSearchParams();
  if (opts?.resolved === true) q.set('resolved', 'true');
  if (opts?.resolved === false) q.set('resolved', 'false');
  if (opts?.limit) q.set('limit', String(opts.limit));
  const qs = q.toString() ? `?${q}` : '';
  return request<ActiveAlert[]>(`/api/v1/alert-engine/alerts${qs}`);
}

export async function resolveActiveAlert(id: string) {
  return request<ActiveAlert>(`/api/v1/alert-engine/alerts/${id}/resolve`, {
    method: 'POST',
    body: '{}',
  });
}

export async function acknowledgeActiveAlert(id: string) {
  return request<ActiveAlert>(`/api/v1/alert-engine/alerts/${id}/acknowledge`, {
    method: 'POST',
    body: '{}',
  });
}

export async function seedAlertDefaults() {
  return request<{ created: number; message: string }>(`/api/v1/alert-engine/seed-defaults`, {
    method: 'POST',
    body: '{}',
  });
}

export async function evaluateAlertMetric(data: {
  metric_name: string;
  metric_value: number;
  target?: string;
  provider?: string;
}) {
  return request<{ check_id: string; status: string; alert_count: number }>(
    `/api/v1/alert-engine/evaluate`,
    { method: 'POST', body: JSON.stringify(data) }
  );
}
