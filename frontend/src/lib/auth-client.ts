const API_BASE = '';

async function postJson<T>(path: string, body: unknown, auth = false): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };

  // Authentication is cookie-based at the application boundary. Keep the
  // access token fallback for existing sessions, but never call the backend
  // directly from the browser.
  if (auth && typeof window !== 'undefined') {
    const t = localStorage.getItem('access_token');
    if (t) headers.Authorization = 'Bearer ' + t;
  }

  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data?.detail;
    let message = '';
    if (typeof detail === 'string' && detail.trim()) {
      message = detail.trim();
    } else if (Array.isArray(detail) && detail.length) {
      message = detail
        .map((d: any) => (typeof d === 'string' ? d : d?.msg || d?.message || JSON.stringify(d)))
        .filter(Boolean)
        .join('; ');
    } else if (detail && typeof detail === 'object') {
      message = detail.msg || detail.message || '';
    }
    if (!message) {
      message = data?.error || data?.message || res.statusText || `Request failed (${res.status})`;
    }
    throw new Error(String(message));
  }
  return data as T;
}

export async function registerUser(input: {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}) {
  return postJson('/api/v1/auth/register', input);
}

export async function loginUser(email: string, password: string, mfa_code?: string) {
  return postJson<{ access_token: string; refresh_token: string; user?: unknown }>(
    '/api/auth/login',
    { email, password, mfa_code: mfa_code || undefined }
  );
}

export async function requestPasswordReset(email: string) {
  return postJson<{ message: string; debug_token?: string; debug_reset_path?: string }>(
    '/api/v1/auth/password-reset/request',
    { email }
  );
}

export async function confirmPasswordReset(token: string, new_password: string) {
  return postJson<{ message: string }>('/api/v1/auth/password-reset/confirm', {
    token,
    new_password,
  });
}

export async function mfaSetup() {
  return postJson<{ secret: string; otpauth_uri: string; enabled: boolean }>(
    '/api/v1/auth/mfa/setup',
    {},
    true
  );
}

export async function mfaVerify(code: string) {
  return postJson<{ enabled: boolean }>('/api/v1/auth/mfa/verify', { code }, true);
}
