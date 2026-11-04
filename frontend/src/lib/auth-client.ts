import { getSupabaseBrowserClient } from './supabase-browser';

const API_BASE = '';

type ApiError = { detail?: unknown; error?: string; message?: string };
type PostResult<T> = { response: Response; data: T };

function errorMessage(data: ApiError, statusText: string, status: number): string {
  const detail = data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail.trim();
  if (Array.isArray(detail) && detail.length)
    return detail
      .map((item: any) => (typeof item === 'string' ? item : item?.msg || item?.message || JSON.stringify(item)))
      .filter(Boolean)
      .join('; ');
  if (detail && typeof detail === 'object') {
    const message = (detail as any).msg || (detail as any).message;
    if (message) return String(message);
  }
  return String(data?.error || data?.message || statusText || `Request failed (${status})`);
}

async function postJsonRaw<T>(path: string, body?: unknown, init?: RequestInit): Promise<PostResult<T>> {
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    ...init,
    headers,
    credentials: 'include',
    cache: 'no-store',
    body: JSON.stringify(body ?? {}),
  });
  const data = await res.json().catch(() => ({}));
  return { response: res, data: data as T };
}

async function postJson<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const { response, data } = await postJsonRaw<T>(path, body, init);
  if (!response.ok) throw new Error(errorMessage(data as ApiError, response.statusText, response.status));
  return data;
}

/**
 * Create a Bhudi local user + tenant, create the Supabase identity, and
 * promote the Supabase session into Bhudi cookies.
 */
export async function registerUser(input: {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  company?: string;
}) {
  // 1) Local Bhudi user + tenant (idempotent-ish: 409 means already mapped).
  const bhudi = await postJsonRaw('/api/auth/register', input);
  if (!bhudi.response.ok && bhudi.response.status !== 409) {
    throw new Error(
      errorMessage(bhudi.data as ApiError, bhudi.response.statusText, bhudi.response.status),
    );
  }

  // 2) Supabase identity (password authority).
  const supabase = getSupabaseBrowserClient();
  const { data: signUpData, error: signUpError } = await supabase.auth.signUp({
    email: input.email,
    password: input.password,
    options: {
      data: {
        first_name: input.first_name,
        last_name: input.last_name,
        company: input.company,
      },
    },
  });
  if (signUpError) {
    // If the identity already exists, fall through to password sign-in.
    const msg = String(signUpError.message || '').toLowerCase();
    const already =
      msg.includes('already') || msg.includes('registered') || msg.includes('exists');
    if (!already) throw new Error(signUpError.message);
  }

  // Prefer session from signUp; otherwise sign in.
  let accessToken = signUpData?.session?.access_token;
  if (!accessToken) {
    const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
      email: input.email,
      password: input.password,
    });
    if (signInError) throw new Error(signInError.message);
    accessToken = signInData.session?.access_token;
  }
  if (!accessToken) {
    throw new Error(
      'Account created. Check your email to confirm the address before signing in.',
    );
  }

  // 3) Promote Supabase session → Bhudi cookies (links supabase_auth_id by email).
  await postJson(
    '/api/auth/login',
    {},
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );

  return bhudi.data;
}

export async function loginUser(email: string, password: string, mfa_code?: string) {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw new Error(error.message);
  if (!data.session?.access_token) {
    throw new Error('Supabase authentication succeeded but no session was returned');
  }
  return postJson<{ access_token?: string; refresh_token?: string; user?: unknown }>(
    '/api/auth/login',
    mfa_code ? { mfa_code } : {},
    { headers: { Authorization: `Bearer ${data.session.access_token}` } },
  );
}

export async function logoutUser() {
  return postJson<{ message?: string }>('/api/auth/logout');
}

export async function refreshSession() {
  return postJson<{ access_token: string; refresh_token: string; user?: unknown }>('/api/auth/refresh');
}

export async function requestPasswordReset(email: string) {
  const supabase = getSupabaseBrowserClient();
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  });
  if (error) throw error;
  return { message: 'If an account exists for that email, password reset instructions have been sent.' };
}

export async function confirmPasswordReset(new_password: string) {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.auth.updateUser({ password: new_password });
  if (error) throw error;
  return data.user;
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
