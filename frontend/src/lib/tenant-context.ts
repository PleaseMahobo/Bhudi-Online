const API_BASE = "";

export async function setTenantContext(tenantId: string | null) {
  const response = await fetch(`${API_BASE}/api/v1/auth/tenant-context`, {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
    },
    credentials: "include",
    cache: "no-store",
    body: JSON.stringify({ tenant_id: tenantId }),
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = typeof body?.detail === "string" ? body.detail : body?.message ?? message;
    } catch {}
    throw new Error(message);
  }

  return response.json() as Promise<{
    user_id: string;
    tenant_id: string | null;
    tenant_name: string | null;
  }>;
}
