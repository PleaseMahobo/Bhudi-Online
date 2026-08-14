const API_BASE = '';

type ApiError = { detail?: unknown; error?: string; message?: string };
type PostResult<T> = { response: Response; data: T };

function errorMessage(data: ApiError, statusText: string, status: number): string {
  const detail = data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail.trim();
  if (Array.isArray(detail) && detail.length) return detail.map((item: any) => typeof item === 'string' ? item : item?.msg || item?.message || JSON.stringify(item)).filter(Boolean).join('; ');
  if (detail && typeof detail === 'object') {
    const message = (detail as any).msg || (detail as any).message;
    if (message) return String(message);
  }
  return String(data?.error || data?.message || statusText || `Request failed (${status})`);
}

async function postJsonRaw<T>(path: string, body?: unknown): Promise<PostResult<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'include',
    cache: 'no-store',
    body: JSON.stringify(body ?? {}),
  });
  const data = await res.json().catch(() => ({}));
  return { response: res, data: data as T };
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const { response, data } = await postJsonRaw<T>(path, body);
  if (!response.ok) throw new Error(errorMessage(data as ApiError, response.statusText, response.status));
  return data;
}

export async function registerUser(input: { email: string; password: string; first_name?: string; last_name?: string }) {
  return postJson('/api/auth/register', input);
}

export async function loginUser(email: string, password: string, mfa_code?: string) {
  return postJson<{ access_token: string; refresh_token: string; user?: unknown }>('/api/auth/login', {
    email,
    password,
    ...(mfa_code ? { mfa_code } : {}),
  });
}

export async function logoutUser() {
  return postJson<{ message?: string }>('/api/auth/logout');
}

export async function refreshSession() {
  return postJson<{ access_token: string; refresh_token: string; user?: unknown }>('/api/auth/refresh');
}

export async function requestPasswordReset(email: string) {
  return postJson<{ message: string }>('/api/auth/password-reset/request', { email });
}

export async function confirmPasswordReset(token: string, new_password: string) {
  return postJson<{ message: string }>('/api/auth/password-reset/confirm', { token, new_password });
}

export async function mfaSetup() {
  return postJson<{ enabled: boolean; email_sent: boolean }>('/api/auth/mfa/setup');
}

export async function mfaVerify(code: string) {
  let result = await postJsonRaw<{ enabled: boolean }>('/api/auth/mfa/verify', { code });
  if (result.response.status === 401) {
    try {
      await refreshSession();
      result = await postJsonRaw<{ enabled: boolean }>('/api/auth/mfa/verify', { code });
    } catch {
      // Fall through to the normal error below.
    }
  }
  if (!result.response.ok) {
    throw new Error(errorMessage(result.data as ApiError, result.response.statusText, result.response.status));
  }
  return result.data;
}
