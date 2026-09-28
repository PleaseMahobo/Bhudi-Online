import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
)
  .replace(/\/$/, '')
  .replace(/\/api\/v1$/, '');

const ACCESS_COOKIE = 'access_token';
const REFRESH_COOKIE = 'refresh_token';
const ACCESS_MAX_AGE = 60 * 15;
const REFRESH_MAX_AGE = 60 * 60 * 24 * 30;

function setSessionCookies(response: NextResponse, accessToken: string, refreshToken: string) {
  response.cookies.set({
    name: ACCESS_COOKIE,
    value: accessToken,
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: ACCESS_MAX_AGE,
  });
  response.cookies.set({
    name: REFRESH_COOKIE,
    value: refreshToken,
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: REFRESH_MAX_AGE,
  });
}

export async function POST(request: NextRequest) {
  try {
    // Prefer the httpOnly cookie set at login. Also accept a JSON body so
    // clients can pass refresh_token explicitly if needed.
    let refreshFromBody: string | undefined;
    const rawBody = await request.text();
    if (rawBody) {
      try {
        const parsed = JSON.parse(rawBody) as { refresh_token?: string };
        if (typeof parsed?.refresh_token === 'string' && parsed.refresh_token.trim()) {
          refreshFromBody = parsed.refresh_token.trim();
        }
      } catch {
        /* non-JSON body ignored */
      }
    }

    const refreshFromCookie = request.cookies.get(REFRESH_COOKIE)?.value;
    const refreshToken = refreshFromBody || refreshFromCookie;

    if (!refreshToken) {
      return NextResponse.json(
        {
          detail: 'Refresh token missing',
          hint: 'Sign in again. No refresh_token cookie on this host (use www.bhudi.online consistently).',
        },
        { status: 401 },
      );
    }

    const headers = new Headers({ 'Content-Type': 'application/json', Accept: 'application/json' });
    const cookie = request.headers.get('cookie');
    const authorization = request.headers.get('authorization');
    if (cookie) headers.set('cookie', cookie);
    if (authorization) headers.set('authorization', authorization);

    // Always send refresh_token in the body so FastAPI receives it even if
    // Cookie header parsing differs on the upstream host.
    const res = await fetch(`${BACKEND}/api/v1/auth/refresh`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: 'no-store',
    });

    const raw = await res.text();
    let data: any = {};
    try {
      data = JSON.parse(raw);
    } catch {
      data = { detail: raw || res.statusText };
    }

    if (!res.ok) {
      return NextResponse.json(
        {
          detail: data?.detail ?? data?.message ?? 'Session refresh failed',
          status: res.status,
          upstream: typeof data === 'object' ? data : undefined,
        },
        { status: res.status >= 500 ? 503 : res.status },
      );
    }

    const response = NextResponse.json(
      {
        token_type: data.token_type,
        user: data.user,
        session_id: data.session_id,
        token_family: data.token_family,
      },
      { status: res.status },
    );

    if (data.access_token && data.refresh_token) {
      setSessionCookies(response, data.access_token, data.refresh_token);
    }

    return response;
  } catch (e) {
    return NextResponse.json(
      {
        detail: 'Backend refresh unavailable',
        message: 'Could not reach the auth API. Try again in a moment.',
        error: String(e),
      },
      { status: 503 },
    );
  }
}
