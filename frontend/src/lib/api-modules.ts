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

// Customer directory/detail helpers. These compose the existing MSP endpoints so
// the customer UI uses the current API surface without changing backend behavior.
export interface CustomerOverviewRow {
  id: string;
  tenant_id: string;
  name: string;
  legal_name?: string | null;
  email?: string | null;
  city?: string | null;
  country?: string | null;
  slug?: string | null;
  status?: string | null;
  counts: { users: number; devices: number; devices_online: number; sites: number };
}

export interface CustomerDetailUser {
  id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  role: string;
  roles: string[];
  active: boolean;
  mfa_enabled?: boolean | null;
  last_login_at?: string | null;
}

export interface CustomerDetailDevice {
  id: string;
  hostname?: string | null;
  status?: string | null;
  ip?: string | null;
  os?: string | null;
  agent_version?: string | null;
  connected_via?: string | null;
  last_seen?: string | null;
  created_at?: string | null;
}

export interface CustomerDetail {
  organization: any & { counts: CustomerOverviewRow["counts"] };
  sites: any[];
  contacts: any[];
  technicians: any[];
  users: CustomerDetailUser[];
  devices: CustomerDetailDevice[];
  isolation: any;
}

export async function getCustomersOverview(): Promise<{ customers: CustomerOverviewRow[] }> {
  const orgs = await listOrganizations({ org_type: "client" });
  const customers = await Promise.all(orgs.map(async (org) => {
    const tenantId = String(org.tenant_id);
    const [sites, contacts] = await Promise.all([
      listSites({ organization_id: String(org.id) }).catch(() => []),
      listContacts({ organization_id: String(org.id) }).catch(() => []),
    ]);
    return {
      id: String(org.id),
      tenant_id: tenantId,
      name: org.name,
      legal_name: org.legal_name,
      email: org.email,
      city: org.city,
      country: org.country,
      slug: org.slug,
      status: org.status,
      counts: { users: 0, devices: 0, devices_online: 0, sites: sites.length },
      _contacts: contacts.length,
    } as CustomerOverviewRow;
  }));
  return { customers };
}

export async function getCustomerDetail(orgId: string): Promise<CustomerDetail> {
  const organization = await request<any>(`/api/v1/msp/organizations/${orgId}`);
  const tenantId = String(organization.tenant_id);
  const [sites, contacts, technicians, isolation] = await Promise.all([
    listSites({ organization_id: orgId }).catch(() => []),
    listContacts({ organization_id: orgId }).catch(() => []),
    listTechnicians({ organization_id: orgId }).catch(() => []),
    getTenantIsolation(tenantId).catch(() => ({})),
  ]);
  const counts = { users: 0, devices: 0, devices_online: 0, sites: sites.length };
  return { organization: { ...organization, counts }, sites, contacts, technicians, users: [], devices: [], isolation };
}

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

// ─── ITSM ─────────────────────────────────────────────────────────────
export async function listTickets(params?: { status?: string; ticket_type?: string; asset_id?: string; device_id?: string; priority?: string; q?: string }) { return request<any[]>(`/api/v1/itsm/tickets${qs(params)}`); }
export async function createTicket(data: Record<string, unknown>) { return request<any>(`/api/v1/itsm/tickets`, { method: "POST", body: JSON.stringify(data) }); }
export async function setTicketStatus(ticketId: string, status: string) { return request<any>(`/api/v1/itsm/tickets/${ticketId}/status`, { method: "POST", body: JSON.stringify({ status }) }); }
export async function deleteTicket(ticketId: string) { return request<void>(`/api/v1/itsm/tickets/${ticketId}`, { method: "DELETE" }); }
export async function linkTicketAsset(ticketId: string, assetId: string, role = "related") { return request<any>(`/api/v1/itsm/tickets/${ticketId}/assets`, { method: "POST", body: JSON.stringify({ asset_id: assetId, role }) }); }
export async function unlinkTicketAsset(ticketId: string, assetId: string) { return request<void>(`/api/v1/itsm/tickets/${ticketId}/assets/${assetId}`, { method: "DELETE" }); }
export async function listTicketsForAsset(assetId: string) { return request<any[]>(`/api/v1/itsm/assets/${assetId}/tickets`); }
export async function createTicketForAsset(assetId: string, data: Record<string, unknown>) { return request<any>(`/api/v1/itsm/assets/${assetId}/tickets`, { method: "POST", body: JSON.stringify(data) }); }
export async function listWorkNotes(ticketId: string) { return request<any[]>(`/api/v1/itsm/tickets/${ticketId}/notes`); }
export async function addWorkNote(ticketId: string, body: string, author?: string) { return request<any>(`/api/v1/itsm/tickets/${ticketId}/notes`, { method: "POST", body: JSON.stringify({ body, author: author ?? null }) }); }
export async function runWarrantyExpiryJob(withinDays = 30) { return request<any[]>(`/api/v1/itsm/jobs/warranty-expiry?within_days=${encodeURIComponent(withinDays)}`, { method: "POST" }); }

// ─── Software Deployment ───────────────────────────────────────────────
export async function listPackages(params?: { package_type?: string; active_only?: boolean }) { return request<any[]>(`/api/v1/software-deployment/packages${qs(params)}`); }
export async function createPackage(data: Record<string, unknown>) { return request<any>(`/api/v1/software-deployment/packages`, { method: "POST", body: JSON.stringify(data) }); }
export async function deletePackage(packageId: string) { return request<void>(`/api/v1/software-deployment/packages/${packageId}`, { method: "DELETE" }); }
export async function listDeploymentJobs(params?: { status?: string; package_id?: string }) { return request<any[]>(`/api/v1/software-deployment/jobs${qs(params)}`); }
export async function createDeploymentJob(data: Record<string, unknown>) { return request<any>(`/api/v1/software-deployment/jobs`, { method: "POST", body: JSON.stringify(data) }); }
export async function startDeploymentJob(jobId: string) { return request<any>(`/api/v1/software-deployment/jobs/${jobId}/start`, { method: "POST" }); }
export async function cancelDeploymentJob(jobId: string) { return request<any>(`/api/v1/software-deployment/jobs/${jobId}/cancel`, { method: "POST" }); }
export async function rollbackDeploymentJob(jobId: string, data: Record<string, unknown> = {}) { return request<any>(`/api/v1/software-deployment/jobs/${jobId}/rollback`, { method: "POST", body: JSON.stringify(data) }); }
export async function getDeploymentSummary(jobId: string) { return request<any>(`/api/v1/software-deployment/jobs/${jobId}/summary`); }
export async function listDeploymentEvents(jobId: string) { return request<any[]>(`/api/v1/software-deployment/jobs/${jobId}/events`); }
