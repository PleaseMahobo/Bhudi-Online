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

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  const next = `${window.location.pathname}${window.location.search || ""}`;
  const target = `/login?next=${encodeURIComponent(next || "/dashboard")}`;
  if (!window.location.pathname.startsWith("/login")) {
    window.location.assign(target);
  }
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
      redirectToLogin();
      throw new Error("Authentication credentials missing");
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      redirectToLogin();
    }
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
