// frontend/src/lib/api-modules.ts
// Enterprise modules → same-origin Next.js API proxy → FastAPI /api/v1/*

const API_BASE = "";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");
  const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, credentials: "include", cache: "no-store" });
  if (!response.ok) {
    let message = response.statusText;
    try { const body = await response.json(); message = typeof body?.detail === "string" ? body.detail : body?.message ?? body?.error ?? JSON.stringify(body); } catch {}
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

function qs(params?: Record<string, string | number | boolean | undefined | null>) {
  if (!params) return "";
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") sp.set(k, String(v)); });
  const value = sp.toString();
  return value ? `?${value}` : "";
}

// ─── MSP ───────────────────────────────────────────────────────────────
export async function listOrganizations(params?: { org_type?: string; status?: string; parent_id?: string; tenant_id?: string }) { return request<any[]>(`/api/v1/msp/organizations${qs(params)}`); }
export async function createOrganization(data: Record<string, unknown>) { return request<any>(`/api/v1/msp/organizations`, { method: "POST", body: JSON.stringify(data) }); }
export async function deleteOrganization(orgId: string) { return request<void>(`/api/v1/msp/organizations/${orgId}`, { method: "DELETE" }); }
export async function createCustomerWizard(data: Record<string, unknown>) { return request<any>(`/api/v1/msp/customers/wizard`, { method: "POST", body: JSON.stringify(data) }); }
export async function inviteUser(data: { email: string; role: string; tenant_id: string; first_name?: string; last_name?: string; temporary_password?: string }) { return request<any>(`/api/v1/msp/users/invite`, { method: "POST", body: JSON.stringify(data) }); }
export async function listSites(params?: { organization_id?: string; tenant_id?: string; enabled_only?: boolean }) { return request<any[]>(`/api/v1/msp/sites${qs(params)}`); }
export async function listContacts(params?: { organization_id?: string; tenant_id?: string; contact_type?: string }) { return request<any[]>(`/api/v1/msp/contacts${qs(params)}`); }
export async function listTechnicians(params?: { organization_id?: string; tenant_id?: string; status?: string }) { return request<any[]>(`/api/v1/msp/technicians${qs(params)}`); }
export async function listBillingPlans(activeOnly = false) { return request<any[]>(`/api/v1/msp/billing/plans${qs({ active_only: activeOnly || undefined })}`); }
export async function seedBillingPlans() { return request<any[]>(`/api/v1/msp/billing/plans/seed`, { method: "POST" }); }
export async function getTenantIsolation(tenantId: string) { return request<any>(`/api/v1/msp/tenants/${tenantId}/isolation`); }
export async function getTenantSubscription(tenantId: string) { return request<any>(`/api/v1/msp/tenants/${tenantId}/subscription`); }

// ─── Stripe billing status ─────────────────────────────────────────────
export async function getStripeBillingStatus() { return request<any>(`/api/v1/msp/billing/stripe/status`); }

// ─── PSA ───────────────────────────────────────────────────────────────
export async function listPsaCatalog() { return request<any[]>(`/api/v1/psa/catalog`); }
export async function listPsaConnections(params?: { enabled_only?: boolean; tenant_id?: string }) { return request<any[]>(`/api/v1/psa/connections${qs(params)}`); }
export async function createPsaConnection(data: Record<string, unknown>) { return request<any>(`/api/v1/psa/connections`, { method: "POST", body: JSON.stringify(data) }); }
export async function listPsaSyncEvents(connectionId?: string) { return request<any[]>(`/api/v1/psa/sync-events${qs({ connection_id: connectionId })}`); }
export async function listPsaTicketLinks(params?: { connection_id?: string; ticket_id?: string }) { return request<any[]>(`/api/v1/psa/ticket-links${qs(params)}`); }

// ─── Notifications ─────────────────────────────────────────────────────
export async function listNotificationCatalog() { return request<any[]>(`/api/v1/notifications/catalog`); }
export async function listNotificationChannels(params?: { tenant_id?: string; enabled_only?: boolean }) { return request<any[]>(`/api/v1/notifications/channels${qs(params)}`); }
export async function createNotificationChannel(data: Record<string, unknown>) { return request<any>(`/api/v1/notifications/channels`, { method: "POST", body: JSON.stringify(data) }); }
export async function listNotificationTemplates(tenantId?: string) { return request<any[]>(`/api/v1/notifications/templates${qs({ tenant_id: tenantId })}`); }
export async function sendNotification(data: { channel_id: string; recipient: string; subject?: string; body?: string; template_code?: string; template_vars?: Record<string, unknown> }) { return request<any>(`/api/v1/notifications/send`, { method: "POST", body: JSON.stringify(data) }); }
export async function listNotificationDeliveries(params?: { channel_id?: string; status_filter?: string; limit?: number }) { return request<any[]>(`/api/v1/notifications/deliveries${qs(params)}`); }

// ─── AI ────────────────────────────────────────────────────────────────
export async function aiRootCause(data: { title: string; symptoms: string; context?: Record<string, unknown>; tenant_id?: string }) { return request<any>(`/api/v1/ai/root-cause`, { method: "POST", body: JSON.stringify(data) }); }
export async function aiGenerateScript(data: { goal: string; platform?: string; constraints?: string; tenant_id?: string }) { return request<any>(`/api/v1/ai/script`, { method: "POST", body: JSON.stringify(data) }); }
export async function aiRemediation(data: { issue: string; environment?: Record<string, unknown>; tenant_id?: string }) { return request<any>(`/api/v1/ai/remediation`, { method: "POST", body: JSON.stringify(data) }); }
export async function aiTicketSummary(data: { title: string; description?: string; work_notes?: string[]; ticket_id?: string; tenant_id?: string }) { return request<any>(`/api/v1/ai/ticket-summary`, { method: "POST", body: JSON.stringify(data) }); }
export async function aiKnowledgeSearch(query: string, limit = 5) { return request<any>(`/api/v1/ai/knowledge/search`, { method: "POST", body: JSON.stringify({ query, limit }) }); }
export async function aiPredictiveFailure(data: { target_id: string; target_type?: string; metrics?: Record<string, unknown>; horizon_hours?: number }) { return request<any>(`/api/v1/ai/predictive-failure`, { method: "POST", body: JSON.stringify(data) }); }
export async function aiCapacityForecast(data: { resource: string; history?: { value: number }[]; horizon_hours?: number }) { return request<any>(`/api/v1/ai/capacity-forecast`, { method: "POST", body: JSON.stringify({ resource: data.resource, history: data.history, horizon_hours: data.horizon_hours }) }); }
export async function listAiRuns(taskType?: string, limit = 50) { return request<any[]>(`/api/v1/ai/runs${qs({ task_type: taskType, limit })}`); }
export async function listKnowledgeArticles(publishedOnly = true) { return request<any[]>(`/api/v1/ai/knowledge${qs({ published_only: publishedOnly })}`); }

// ─── Reporting ─────────────────────────────────────────────────────────
export async function listReportCatalog() { return request<any>(`/api/v1/reports/catalog`); }
export async function listReportTemplates() { return request<any[]>(`/api/v1/reports/templates`); }
export async function listReportSchedules() { return request<any[]>(`/api/v1/reports/schedules`); }
export async function listReportRuns(limit = 50) { return request<any[]>(`/api/v1/reports/runs${qs({ limit })}`); }
export async function runReport(data: Record<string, unknown>) { return request<any>(`/api/v1/reports/run`, { method: "POST", body: JSON.stringify(data) }); }

// ─── Compliance ────────────────────────────────────────────────────────
export async function listComplianceFrameworks() { return request<any[]>(`/api/v1/compliance/frameworks`); }
export async function listComplianceAssessments(params?: { framework_id?: string; status?: string }) { return request<any[]>(`/api/v1/compliance/assessments${qs(params)}`); }
export async function listComplianceScores() { return request<any[]>(`/api/v1/compliance/scores`); }
export async function seedComplianceFrameworks() { return request<any>(`/api/v1/compliance/frameworks/seed`, { method: "POST" }); }

// ─── Backup ────────────────────────────────────────────────────────────
export async function listBackupCatalog() { return request<any[]>(`/api/v1/backup/catalog`); }
export async function listBackupProviders(enabledOnly = false) { return request<any[]>(`/api/v1/backup/providers${qs({ enabled_only: enabledOnly || undefined })}`); }
export async function seedBackupProviders() { return request<any[]>(`/api/v1/backup/providers/seed`, { method: "POST" }); }
export async function listBackupResources(params?: { provider_id?: string; status?: string }) { return request<any[]>(`/api/v1/backup/resources${qs(params)}`); }
export async function listBackupJobs(params?: { provider_id?: string; status?: string }) { return request<any[]>(`/api/v1/backup/jobs${qs(params)}`); }
export async function listBackupRestores(params?: { status?: string }) { return request<any[]>(`/api/v1/backup/restores${qs(params)}`); }
export async function getBackupSummary() { return request<any>(`/api/v1/backup/summary`); }
