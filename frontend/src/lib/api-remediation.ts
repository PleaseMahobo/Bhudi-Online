// Alert remediation types + helpers (keeps api.ts lean)

export type RemediationActionType =
  | 'run_script'
  | 'run_command'
  | 'inventory_refresh'
  | 'notify_only';

export interface RemediationAction {
  name: string;
  type: RemediationActionType;
  enabled?: boolean;
  shell?: string;
  script_content?: string | null;
  command_type?: string | null;
  min_severity?: 'info' | 'warning' | 'critical' | 'emergency';
  cooldown_seconds?: number;
  dry_run?: boolean;
  ignore_suppression?: boolean;
}

export interface RemediationRun {
  id: string;
  alert_id?: string | null;
  rule_id?: string | null;
  rule_name?: string | null;
  fingerprint?: string | null;
  device_id?: string | null;
  action_type: string;
  action_name?: string | null;
  status: string;
  skip_reason?: string | null;
  dry_run?: boolean;
  task_id?: string | null;
  severity?: string | null;
  details?: Record<string, unknown> | null;
  created_at: string;
}

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
      message =
        typeof body?.detail === 'string'
          ? body.detail
          : body?.message ?? body?.error ?? JSON.stringify(body);
    } catch {}
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function listRemediationRuns(limit = 50) {
  return request<RemediationRun[]>(`/api/v1/alert-engine/remediation-runs?limit=${limit}`);
}
