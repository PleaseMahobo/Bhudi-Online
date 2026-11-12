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
type RegisterResult =
  | { email: string; requiresEmailVerification: true }
  | { email: string; requiresEmailVerification: false };

export async function registerUser(input: {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  company?: string;
}) : Promise<RegisterResult> {
  // Supabase is the identity/password authority. Create that identity first.
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
    const msg = String(signUpError.message || '').toLowerCase();

    if (msg.includes('rate limit') || msg.includes('email rate limit') || msg.includes('over_email_send_rate_limit')) {
      throw new Error('Email verification is temporarily rate-limited. Please wait before requesting another verification email.');
    }

    const already = msg.includes('already') || msg.includes('registered') || msg.includes('exists');
    if (already) {
      throw new Error('If this email can be registered, a verification message will be sent. If you already have an account, please use Sign in.');
    }

    throw new Error(signUpError.message);
  }

  // Supabase may intentionally mask an existing confirmed email. When it
  // returns a user with no identities, treat that as an existing account rather
  // than pretending a new signup was created.
  if (
    signUpData?.user &&
    Array.isArray(signUpData.user.identities) &&
    signUpData.user.identities.length === 0
  ) {
    throw new Error('An account already exists for this email address. Please sign in instead.');
  }

  // Do not attempt password login from the signup flow when confirmation is
  // required. That produced the misleading "Invalid login credentials" state
  // and could generate unnecessary authentication/email traffic.
  const accessToken = signUpData?.session?.access_token;
  if (!accessToken) {
    return {
      email: input.email,
      requiresEmailVerification: true,
    };
  }

  await postJson(
    '/api/auth/provision',
    {
      first_name: input.first_name,
      last_name: input.last_name,
      company: input.company,
    },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );

  await postJson(
    '/api/auth/login',
    {},
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );

  return { email: input.email, requiresEmailVerification: false };
}

export async function loginUser(
  email: string,
  password: string,
  mfa_code?: string,
  profile?: { first_name?: string; last_name?: string; company?: string },
) {
  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw new Error(error.message);
  if (!data.session?.access_token) {
    throw new Error('Supabase authentication succeeded but no session was returned');
  }

  // Idempotent recovery path: a verified Supabase account can provision or
  // repair its Bhudi profile/tenant before session promotion.
  await postJson(
    '/api/auth/provision',
    profile ?? {},
    { headers: { Authorization: `Bearer ${data.session.access_token}` } },
  );

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
