// frontend/src/lib/api.ts

// Browser API calls stay on the same origin so the Next.js proxy can attach
// the HttpOnly access/refresh cookies issued by /api/auth/*.
const API_BASE = "";

let refreshPromise: Promise<void> | null = null;

async function refreshSessionOnce(): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { Accept: "application/json" },
      credentials: "include",
      cache: "no-store",
    }).then(async response => {
      if (!response.ok) throw new Error(`Session refresh failed (${response.status})`);
      await response.json().catch(() => undefined);
    }).finally(() => { refreshPromise = null; });
  }
  await refreshPromise;
}

async function request<T>(endpoint: string, options: RequestInit = {}, allowRefresh = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");
  const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, credentials: "include", cache: "no-store" });

  if (response.status === 401 && allowRefresh && endpoint !== "/api/auth/login" && endpoint !== "/api/auth/refresh" && endpoint !== "/api/auth/logout") {
    try {
      await refreshSessionOnce();
      return request<T>(endpoint, options, false);
    } catch {
      // Refresh is genuinely unavailable; surface the original authentication failure.
    }
  }

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      const detail = body?.detail;
      message = typeof detail === "string" ? detail : body?.message ?? body?.error ?? JSON.stringify(body);
    } catch {}
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
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
  if (Array.isArray(payload)) return payload.map(normalizeDevice);
  if (payload && Array.isArray(payload.devices)) return payload.devices.map(normalizeDevice);
  return [];
}

export interface HealthResponse {
  status: string;
  service?: string;
  version?: string;
  message?: string;
}

// =========================================================
// Alert Engine Types
// =========================================================

export interface EscalationLevel { repeat_count: number; severity: string; notify: string[]; }
export interface EscalationPolicy { id: string; name: string; description?: string | null; levels: EscalationLevel[]; enabled: boolean; created_at: string; updated_at: string; }
export interface AlertRule {
  id: string; name: string; description?: string | null; provider?: string | null; check_type?: string | null;
  target?: string | null; metric_name?: string | null; warning_threshold?: number | null; critical_threshold?: number | null;
  anomaly_enabled: boolean; anomaly_tolerance?: number | null; state_change_enabled: boolean; ai_suppression_enabled: boolean;
  maintenance_window_name?: string | null; escalation_policy_id?: string | null; enabled: boolean; priority: number;
  tags?: Record<string, any> | null; created_at: string; updated_at: string;
}
export type AlertRuleCreate = Omit<AlertRule, "id" | "created_at" | "updated_at">;
export type EscalationPolicyCreate = Omit<EscalationPolicy, "id" | "created_at" | "updated_at">;

// =========================================================
// Asset Management Types
// =========================================================

export type AssetStatus = "ordered" | "in_stock" | "deployed" | "in_repair" | "retired" | "disposed" | string;
export interface Asset {
  id: string; name: string; asset_tag?: string | null; serial_number?: string | null; asset_type?: string | null;
  manufacturer?: string | null; model?: string | null; status: AssetStatus; location?: string | null;
  assigned_to?: string | null; device_id?: string | null; vendor_id?: string | null; purchase_cost?: number | null;
  purchase_date?: string | null; warranty_end?: string | null; warranty_active?: boolean | null; qr_code?: string | null;
  notes?: string | null; created_at?: string; updated_at?: string;
}
export type AssetCreate = { name: string; asset_tag?: string | null; serial_number?: string | null; asset_type?: string | null; manufacturer?: string | null; model?: string | null; status?: AssetStatus; location?: string | null; assigned_to?: string | null; device_id?: string | null; vendor_id?: string | null; purchase_cost?: number | null; purchase_date?: string | null; warranty_end?: string | null; notes?: string | null; };
export interface Vendor { id: string; name: string; contact_email?: string | null; contact_phone?: string | null; website?: string | null; active: boolean; notes?: string | null; created_at?: string; updated_at?: string; }
export type VendorCreate = { name: string; contact_email?: string | null; contact_phone?: string | null; website?: string | null; active?: boolean; notes?: string | null; };
export interface License { id: string; name: string; vendor_id?: string | null; license_key?: string | null; seats_total: number; seats_used: number; seats_available?: number; expires_at?: string | null; active: boolean; notes?: string | null; created_at?: string; updated_at?: string; }
export type LicenseCreate = { name: string; vendor_id?: string | null; license_key?: string | null; seats_total?: number; seats_used?: number; expires_at?: string | null; active?: boolean; notes?: string | null; };
export interface Contract { id: string; name: string; vendor_id?: string | null; contract_type?: string | null; status: string; start_date?: string | null; end_date?: string | null; value?: number | null; notes?: string | null; created_at?: string; updated_at?: string; }
export type ContractCreate = { name: string; vendor_id?: string | null; contract_type?: string | null; status?: string; start_date?: string | null; end_date?: string | null; value?: number | null; notes?: string | null; };
export interface SoftwareItem { id: string; name: string; version?: string | null; publisher?: string | null; asset_id?: string | null; device_id?: string | null; install_date?: string | null; created_at?: string; }
export interface DepreciationInfo { asset_id: string; method: string; purchase_cost: number; residual_value: number; useful_life_months: number; months_elapsed: number; book_value: number; accumulated_depreciation: number; }
export interface WarrantyInfo { asset_id: string; serial_number?: string | null; warranty_end?: string | null; warranty_active: boolean; days_remaining?: number | null; source?: string | null; }
export interface LifecycleEvent { id: string; asset_id: string; from_status?: string | null; to_status: string; reason?: string | null; changed_by?: string | null; created_at: string; }

// =========================================================
// ITSM Types
// =========================================================

export type TicketType = "incident" | "service_request" | "problem" | "change" | string;
export type TicketStatus = "new" | "open" | "in_progress" | "on_hold" | "resolved" | "closed" | string;
export interface TicketAssetLink { id: string; ticket_id: string; asset_id: string; role?: string | null; linked_at: string; notes?: string | null; asset_name?: string | null; asset_tag?: string | null; asset_status?: string | null; }
export interface ServiceTicket { id: string; number: string; title: string; description?: string | null; ticket_type: TicketType; status: TicketStatus; priority: string; device_id?: string | null; requester?: string | null; assignee?: string | null; asset_links?: TicketAssetLink[]; created_at: string; updated_at: string; resolved_at?: string | null; }
export type ServiceTicketCreate = { title: string; description?: string | null; ticket_type?: TicketType; status?: TicketStatus; priority?: string; device_id?: string | null; requester?: string | null; assignee?: string | null; asset_ids?: string[]; };
export interface WorkNote { id: string; ticket_id: string; body: string; author?: string | null; created_at: string; }

// =========================================================
// Software Deployment (Phase 11)
// =========================================================

export type PackageType = "msi" | "exe" | "chocolatey" | "winget" | "custom" | string;
export interface SoftwarePackage { id: string; name: string; version: string; publisher?: string | null; description?: string | null; package_type: PackageType; source_url?: string | null; file_name?: string | null; sha256?: string | null; file_size_bytes?: number | null; choco_id?: string | null; winget_id?: string | null; install_args?: string | null; uninstall_args?: string | null; uninstall_command?: string | null; success_exit_codes?: number[] | null; requires_reboot: boolean; requires_elevation: boolean; timeout_seconds: number; architecture?: string | null; is_active: boolean; tags?: Record<string, any> | null; metadata_json?: Record<string, any> | null; tenant_id?: string | null; created_at: string; updated_at: string; }
export type SoftwarePackageCreate = { name: string; version?: string; publisher?: string | null; description?: string | null; package_type: PackageType; source_url?: string | null; file_name?: string | null; sha256?: string | null; file_size_bytes?: number | null; choco_id?: string | null; winget_id?: string | null; install_args?: string | null; uninstall_args?: string | null; uninstall_command?: string | null; success_exit_codes?: number[] | null; requires_reboot?: boolean; requires_elevation?: boolean; timeout_seconds?: number; architecture?: string | null; is_active?: boolean; tags?: Record<string, any> | null; };
export interface DeploymentTarget { id: string; job_id: string; device_id?: string | null; agent_id?: string | null; hostname?: string | null; status: string; exit_code?: number | null; stdout?: string | null; stderr?: string | null; error_message?: string | null; download_bytes?: number | null; duration_ms?: number | null; reboot_required: boolean; started_at?: string | null; finished_at?: string | null; reported_at?: string | null; created_at: string; updated_at: string; }
export interface DeploymentJob { id: string; tenant_id?: string | null; package_id: string; name: string; action: string; status: string; created_by?: string | null; notes?: string | null; rollback_of_job_id?: string | null; scheduled_at?: string | null; started_at?: string | null; finished_at?: string | null; targets_total: number; targets_success: number; targets_failed: number; targets_pending: number; tags?: Record<string, any> | null; created_at: string; updated_at: string; targets?: DeploymentTarget[]; }
export type DeploymentJobCreate = { package_id: string; name: string; action?: string; device_ids?: string[]; hostnames?: string[]; created_by?: string | null; notes?: string | null; scheduled_at?: string | null; };
export interface DeploymentJobSummary { job_id: string; status: string; targets_total: number; targets_success: number; targets_failed: number; targets_pending: number; success_rate: number; finished_at?: string | null; }
export interface DeploymentEvent { id: string; job_id: string; target_id?: string | null; level: string; message: string; detail?: Record<string, any> | null; created_at: string; }

// =========================================================
// Endpoint Security (Phase 12)
// =========================================================

export interface SecurityProviderCatalogItem { provider_key: string; display_name: string; }
export interface SecurityProvider { id: string; tenant_id?: string | null; provider_key: string; display_name: string; enabled: boolean; config?: Record<string, any> | null; last_sync_at?: string | null; last_sync_status?: string | null; last_sync_error?: string | null; notes?: string | null; created_at: string; updated_at: string; }
export type SecurityProviderCreate = { provider_key: string; display_name: string; enabled?: boolean; config?: Record<string, any> | null; notes?: string | null; tenant_id?: string | null; };
export interface EndpointSecurityAgent { id: string; device_id?: string | null; hostname?: string | null; provider_id: string; external_agent_id?: string | null; agent_version?: string | null; status: string; real_time_protection?: boolean | null; definitions_up_to_date?: boolean | null; last_scan_at?: string | null; last_seen_at?: string | null; details?: Record<string, any> | null; created_at: string; updated_at: string; provider_key?: string | null; provider_name?: string | null; }
export type EndpointSecurityAgentCreate = { provider_id: string; device_id?: string | null; hostname?: string | null; external_agent_id?: string | null; agent_version?: string | null; status?: string; real_time_protection?: boolean | null; definitions_up_to_date?: boolean | null; last_scan_at?: string | null; last_seen_at?: string | null; details?: Record<string, any> | null; };
export interface SecurityFinding { id: string; provider_id: string; device_id?: string | null; hostname?: string | null; external_id?: string | null; title: string; description?: string | null; severity: string; status: string; category?: string | null; confidence?: number | null; detected_at?: string | null; resolved_at?: string | null; raw?: Record<string, any> | null; created_at: string; updated_at: string; provider_key?: string | null; }
export type SecurityFindingCreate = { provider_id: string; device_id?: string | null; hostname?: string | null; external_id?: string | null; title: string; description?: string | null; severity?: string; status?: string; category?: string | null; confidence?: number | null; detected_at?: string | null; raw?: Record<string, any> | null; };
export interface EndpointSecurityScore { id: string; device_id: string; hostname?: string | null; score: number; grade: string; factors?: Record<string, any> | null; open_critical: number; open_high: number; agents_healthy: number; agents_total: number; computed_at: string; created_at: string; updated_at: string; }
export interface OrgSecurityScore { devices_scored: number; average_score: number; median_score: number; grade_distribution: Record<string, number>; open_critical_total: number; open_high_total: number; providers_enabled: number; agents_healthy: number; agents_total: number; }

// =========================================================
// Auth — session cookies only. No browser token storage.
// =========================================================

export async function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export async function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export async function getCurrentUser() {
  return request<User>("/api/auth/me");
}

export async function refreshAccessToken() {
  return request<LoginResponse>("/api/auth/refresh", { method: "POST" }, false);
}

export async function getHealth() { return request<HealthResponse>("/api/health"); }
// Devices are tenant-scoped. Use the same-origin tenant-context proxy so the
// portal HttpOnly session is converted into an Authorization header for Railway.
export async function getDevices() {
  return normalizeDevicesPayload(await request<any>("/api/tenant-context/devices"));
}
export async function getDeviceStatus() { return getDevices(); }

export async function listEscalationPolicies(enabledOnly = false) { return request<EscalationPolicy[]>(`/api/v1/alert-engine/escalation-policies${enabledOnly ? "?enabled_only=true" : ""}`); }
export async function createEscalationPolicy(data: EscalationPolicyCreate) { return request<EscalationPolicy>(`/api/v1/alert-engine/escalation-policies`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateEscalationPolicy(id: string, data: Partial<EscalationPolicyCreate>) { return request<EscalationPolicy>(`/api/v1/alert-engine/escalation-policies/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteEscalationPolicy(id: string) { return request<void>(`/api/v1/alert-engine/escalation-policies/${id}`, { method: "DELETE" }); }
export async function listAlertRules(enabledOnly = false) { return request<AlertRule[]>(`/api/v1/alert-engine/rules${enabledOnly ? "?enabled_only=true" : ""}`); }
export async function createAlertRule(data: AlertRuleCreate) { return request<AlertRule>(`/api/v1/alert-engine/rules`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateAlertRule(id: string, data: Partial<AlertRuleCreate>) { return request<AlertRule>(`/api/v1/alert-engine/rules/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteAlertRule(id: string) { return request<void>(`/api/v1/alert-engine/rules/${id}`, { method: "DELETE" }); }

export async function listAssets(params?: { status?: string; device_id?: string; tenant_id?: string }) { const qs = new URLSearchParams(); if (params?.status) qs.set("status", params.status); if (params?.device_id) qs.set("device_id", params.device_id); if (params?.tenant_id) qs.set("tenant_id", params.tenant_id); return request<Asset[]>(`/api/v1/assets${qs.toString() ? `?${qs}` : ""}`); }
export async function createAsset(data: AssetCreate) { return request<Asset>(`/api/v1/assets`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateAsset(id: string, data: Partial<AssetCreate>) { return request<Asset>(`/api/v1/assets/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteAsset(id: string) { return request<void>(`/api/v1/assets/${id}`, { method: "DELETE" }); }
export async function changeAssetStatus(id: string, status: string, reason?: string) { return request<Asset>(`/api/v1/assets/${id}/status`, { method: "POST", body: JSON.stringify({ status, reason: reason || null }) }); }
export async function getAssetByQr(qrCode: string) { return request<Asset>(`/api/v1/assets/by-qr/${encodeURIComponent(qrCode)}`); }
export async function ensureAssetQr(id: string) { return request<{ asset_id: string; qr_code: string }>(`/api/v1/assets/${id}/qr`, { method: "POST" }); }
export async function getAssetWarranty(id: string) { return request<WarrantyInfo>(`/api/v1/assets/${id}/warranty`); }
export async function getAssetDepreciation(id: string) { return request<DepreciationInfo>(`/api/v1/assets/${id}/depreciation`); }
export async function listAssetLifecycle(id: string) { return request<LifecycleEvent[]>(`/api/v1/assets/${id}/lifecycle`); }
export async function listVendors(activeOnly = false) { return request<Vendor[]>(`/api/v1/assets/vendors${activeOnly ? "?active_only=true" : ""}`); }
export async function createVendor(data: VendorCreate) { return request<Vendor>(`/api/v1/assets/vendors`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateVendor(id: string, data: Partial<VendorCreate>) { return request<Vendor>(`/api/v1/assets/vendors/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteVendor(id: string) { return request<void>(`/api/v1/assets/vendors/${id}`, { method: "DELETE" }); }
export async function listLicenses(activeOnly = false) { return request<License[]>(`/api/v1/assets/licenses${activeOnly ? "?active_only=true" : ""}`); }
export async function createLicense(data: LicenseCreate) { return request<License>(`/api/v1/assets/licenses`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateLicense(id: string, data: Partial<LicenseCreate>) { return request<License>(`/api/v1/assets/licenses/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteLicense(id: string) { return request<void>(`/api/v1/assets/licenses/${id}`, { method: "DELETE" }); }
export async function listContracts(status?: string) { return request<Contract[]>(`/api/v1/assets/contracts${status ? `?status=${encodeURIComponent(status)}` : ""}`); }
export async function createContract(data: ContractCreate) { return request<Contract>(`/api/v1/assets/contracts`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateContract(id: string, data: Partial<ContractCreate>) { return request<Contract>(`/api/v1/assets/contracts/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteContract(id: string) { return request<void>(`/api/v1/assets/contracts/${id}`, { method: "DELETE" }); }
export async function listSoftware(params?: { asset_id?: string; device_id?: string }) { const qs = new URLSearchParams(); if (params?.asset_id) qs.set("asset_id", params.asset_id); if (params?.device_id) qs.set("device_id", params.device_id); return request<SoftwareItem[]>(`/api/v1/assets/software${qs.toString() ? `?${qs}` : ""}`); }

export async function listTickets(params?: { status?: string; ticket_type?: string; asset_id?: string; device_id?: string; priority?: string }) { const qs = new URLSearchParams(); if (params?.status) qs.set("status", params.status); if (params?.ticket_type) qs.set("ticket_type", params.ticket_type); if (params?.asset_id) qs.set("asset_id", params.asset_id); if (params?.device_id) qs.set("device_id", params.device_id); if (params?.priority) qs.set("priority", params.priority); return request<ServiceTicket[]>(`/api/v1/itsm/tickets${qs.toString() ? `?${qs}` : ""}`); }
export async function createTicket(data: ServiceTicketCreate) { return request<ServiceTicket>(`/api/v1/itsm/tickets`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateTicket(id: string, data: Partial<ServiceTicketCreate>) { return request<ServiceTicket>(`/api/v1/itsm/tickets/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function setTicketStatus(id: string, status: string, note?: string) { return request<ServiceTicket>(`/api/v1/itsm/tickets/${id}/status`, { method: "POST", body: JSON.stringify({ status, note: note || null }) }); }
export async function deleteTicket(id: string) { return request<void>(`/api/v1/itsm/tickets/${id}`, { method: "DELETE" }); }
export async function linkTicketAsset(ticketId: string, assetId: string, role?: string, notes?: string) { return request<TicketAssetLink>(`/api/v1/itsm/tickets/${ticketId}/assets`, { method: "POST", body: JSON.stringify({ asset_id: assetId, role: role || "related", notes: notes || null }) }); }
export async function unlinkTicketAsset(ticketId: string, assetId: string) { return request<void>(`/api/v1/itsm/tickets/${ticketId}/assets/${assetId}`, { method: "DELETE" }); }
export async function listTicketsForAsset(assetId: string) { return request<ServiceTicket[]>(`/api/v1/itsm/assets/${assetId}/tickets`); }
export async function createTicketForAsset(assetId: string, data: Omit<ServiceTicketCreate, "asset_ids">) { return request<ServiceTicket>(`/api/v1/itsm/assets/${assetId}/tickets`, { method: "POST", body: JSON.stringify(data) }); }
export async function listWorkNotes(ticketId: string) { return request<WorkNote[]>(`/api/v1/itsm/tickets/${ticketId}/notes`); }
export async function addWorkNote(ticketId: string, body: string, author?: string) { return request<WorkNote>(`/api/v1/itsm/tickets/${ticketId}/notes`, { method: "POST", body: JSON.stringify({ body, author: author || null }) }); }
export async function runWarrantyExpiryJob(withinDays = 30) { return request<ServiceTicket[]>(`/api/v1/itsm/jobs/warranty-expiry?within_days=${withinDays}`, { method: "POST" }); }

export async function listPackages(params?: { package_type?: string; active_only?: boolean }) { const qs = new URLSearchParams(); if (params?.package_type) qs.set("package_type", params.package_type); if (params?.active_only) qs.set("active_only", "true"); return request<SoftwarePackage[]>(`/api/v1/software-deployment/packages${qs.toString() ? `?${qs}` : ""}`); }
export async function createPackage(data: SoftwarePackageCreate) { return request<SoftwarePackage>(`/api/v1/software-deployment/packages`, { method: "POST", body: JSON.stringify(data) }); }
export async function updatePackage(id: string, data: Partial<SoftwarePackageCreate>) { return request<SoftwarePackage>(`/api/v1/software-deployment/packages/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deletePackage(id: string) { return request<void>(`/api/v1/software-deployment/packages/${id}`, { method: "DELETE" }); }
export async function listDeploymentJobs(params?: { status?: string; package_id?: string }) { const qs = new URLSearchParams(); if (params?.status) qs.set("status", params.status); if (params?.package_id) qs.set("package_id", params.package_id); return request<DeploymentJob[]>(`/api/v1/software-deployment/jobs${qs.toString() ? `?${qs}` : ""}`); }
export async function getDeploymentJob(id: string) { return request<DeploymentJob>(`/api/v1/software-deployment/jobs/${id}`); }
export async function createDeploymentJob(data: DeploymentJobCreate) { return request<DeploymentJob>(`/api/v1/software-deployment/jobs`, { method: "POST", body: JSON.stringify(data) }); }
export async function startDeploymentJob(id: string) { return request<DeploymentJob>(`/api/v1/software-deployment/jobs/${id}/start`, { method: "POST" }); }
export async function cancelDeploymentJob(id: string) { return request<DeploymentJob>(`/api/v1/software-deployment/jobs/${id}/cancel`, { method: "POST" }); }
export async function getDeploymentSummary(id: string) { return request<DeploymentJobSummary>(`/api/v1/software-deployment/jobs/${id}/summary`); }
export async function listDeploymentEvents(id: string) { return request<DeploymentEvent[]>(`/api/v1/software-deployment/jobs/${id}/events`); }
export async function rollbackDeploymentJob(id: string, opts?: { created_by?: string; notes?: string; device_ids?: string[] }) { return request<DeploymentJob>(`/api/v1/software-deployment/jobs/${id}/rollback`, { method: "POST", body: JSON.stringify({ created_by: opts?.created_by || null, notes: opts?.notes || null, device_ids: opts?.device_ids || [] }) }); }

export async function listSecurityCatalog() { return request<SecurityProviderCatalogItem[]>(`/api/v1/endpoint-security/catalog`); }
export async function seedSecurityProviders() { return request<SecurityProvider[]>(`/api/v1/endpoint-security/providers/seed`, { method: "POST" }); }
export async function listSecurityProviders(enabledOnly = false) { return request<SecurityProvider[]>(`/api/v1/endpoint-security/providers${enabledOnly ? "?enabled_only=true" : ""}`); }
export async function createSecurityProvider(data: SecurityProviderCreate) { return request<SecurityProvider>(`/api/v1/endpoint-security/providers`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateSecurityProvider(id: string, data: Partial<SecurityProviderCreate> & { last_sync_status?: string | null; last_sync_error?: string | null }) { return request<SecurityProvider>(`/api/v1/endpoint-security/providers/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteSecurityProvider(id: string) { return request<void>(`/api/v1/endpoint-security/providers/${id}`, { method: "DELETE" }); }
export async function listSecurityAgents(params?: { device_id?: string; provider_id?: string; status?: string }) { const qs = new URLSearchParams(); if (params?.device_id) qs.set("device_id", params.device_id); if (params?.provider_id) qs.set("provider_id", params.provider_id); if (params?.status) qs.set("status", params.status); return request<EndpointSecurityAgent[]>(`/api/v1/endpoint-security/agents${qs.toString() ? `?${qs}` : ""}`); }
export async function createSecurityAgent(data: EndpointSecurityAgentCreate) { return request<EndpointSecurityAgent>(`/api/v1/endpoint-security/agents`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateSecurityAgent(id: string, data: Partial<EndpointSecurityAgentCreate>) { return request<EndpointSecurityAgent>(`/api/v1/endpoint-security/agents/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteSecurityAgent(id: string) { return request<void>(`/api/v1/endpoint-security/agents/${id}`, { method: "DELETE" }); }
export async function listSecurityFindings(params?: { device_id?: string; provider_id?: string; status?: string; severity?: string }) { const qs = new URLSearchParams(); if (params?.device_id) qs.set("device_id", params.device_id); if (params?.provider_id) qs.set("provider_id", params.provider_id); if (params?.status) qs.set("status", params.status); if (params?.severity) qs.set("severity", params.severity); return request<SecurityFinding[]>(`/api/v1/endpoint-security/findings${qs.toString() ? `?${qs}` : ""}`); }
export async function createSecurityFinding(data: SecurityFindingCreate) { return request<SecurityFinding>(`/api/v1/endpoint-security/findings`, { method: "POST", body: JSON.stringify(data) }); }
export async function updateSecurityFinding(id: string, data: Partial<SecurityFindingCreate> & { resolved_at?: string | null }) { return request<SecurityFinding>(`/api/v1/endpoint-security/findings/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export async function deleteSecurityFinding(id: string) { return request<void>(`/api/v1/endpoint-security/findings/${id}`, { method: "DELETE" }); }
export async function getOrgSecurityScore() { return request<OrgSecurityScore>(`/api/v1/endpoint-security/scores/org`); }
export async function listSecurityScores(minScore?: number) { return request<EndpointSecurityScore[]>(`/api/v1/endpoint-security/scores${minScore != null ? `?min_score=${minScore}` : ""}`); }
export async function getDeviceSecurityScore(deviceId: string) { return request<EndpointSecurityScore>(`/api/v1/endpoint-security/scores/${deviceId}`); }
export async function recomputeDeviceSecurityScore(deviceId: string) { return request<EndpointSecurityScore>(`/api/v1/endpoint-security/scores/${deviceId}/recompute`, { method: "POST" }); }
export async function recomputeAllSecurityScores() { return request<{ devices_scored: number }>(`/api/v1/endpoint-security/scores/recompute-all`, { method: "POST" }); }

export * from "./api-modules";
