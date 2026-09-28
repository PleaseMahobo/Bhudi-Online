/**
 * Shared Bhudi session refresh.
 * Access cookies last 15 minutes; proactive refresh runs before expiry
 * so API calls rarely hit a hard 401 + forced login redirect.
 */

const API_BASE = "";

/** Access cookie maxAge is 15 minutes; refresh a few minutes earlier. */
export const ACCESS_TOKEN_TTL_MS = 15 * 60 * 1000;
export const PROACTIVE_REFRESH_INTERVAL_MS = 12 * 60 * 1000; // 12 min
export const PROACTIVE_REFRESH_MIN_GAP_MS = 60 * 1000; // avoid spam

let refreshPromise: Promise<void> | null = null;
let intervalId: ReturnType<typeof setInterval> | null = null;
let visibilityHandler: (() => void) | null = null;
let lastAttemptAt = 0;
let lastSuccessAt = 0;
let failureHandler: (() => void) | null = null;

/**
 * Single in-flight POST /api/auth/refresh so parallel 401s and the
 * proactive timer share one network call.
 */
export async function refreshSessionOnce(): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { Accept: "application/json" },
      credentials: "include",
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Session refresh failed (${response.status})`);
        }
        await response.json().catch(() => undefined);
        lastSuccessAt = Date.now();
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  await refreshPromise;
}

async function tick(): Promise<void> {
  if (typeof window === "undefined") return;
  // Skip on public auth routes
  const path = window.location.pathname || "";
  if (
    path.startsWith("/login") ||
    path.startsWith("/signup") ||
    path.startsWith("/forgot-password") ||
    path.startsWith("/reset-password")
  ) {
    return;
  }

  const now = Date.now();
  if (now - lastAttemptAt < PROACTIVE_REFRESH_MIN_GAP_MS) return;
  lastAttemptAt = now;

  try {
    await refreshSessionOnce();
  } catch {
    failureHandler?.();
  }
}

/**
 * Start background refresh (~every 12 minutes) and refresh when the
 * tab becomes visible again after a long idle period.
 */
export function startProactiveSessionRefresh(options?: {
  onFailure?: () => void;
}): void {
  if (typeof window === "undefined") return;

  stopProactiveSessionRefresh();
  failureHandler = options?.onFailure ?? null;

  intervalId = setInterval(() => {
    void tick();
  }, PROACTIVE_REFRESH_INTERVAL_MS);

  visibilityHandler = () => {
    if (document.visibilityState !== "visible") return;
    // If access token is likely near/past expiry, refresh on focus
    const stale =
      !lastSuccessAt || Date.now() - lastSuccessAt > PROACTIVE_REFRESH_INTERVAL_MS;
    if (stale) void tick();
  };
  document.addEventListener("visibilitychange", visibilityHandler);

  // Do not refresh immediately on start — login just set cookies.
  // First scheduled tick is after INTERVAL.
}

export function stopProactiveSessionRefresh(): void {
  if (intervalId != null) {
    clearInterval(intervalId);
    intervalId = null;
  }
  if (visibilityHandler && typeof document !== "undefined") {
    document.removeEventListener("visibilitychange", visibilityHandler);
    visibilityHandler = null;
  }
  failureHandler = null;
}

export function getLastSessionRefreshAt(): number {
  return lastSuccessAt;
}
