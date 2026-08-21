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
  response.cookies.set({ name: ACCESS_COOKIE, value: accessToken, httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: ACCESS_MAX_AGE });
  response.cookies.set({ name: REFRESH_COOKIE, value: refreshToken, httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: REFRESH_MAX_AGE });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const headers = new Headers({ 'Content-Type': 'application/json' });
    const cookie = request.headers.get('cookie');
    const authorization = request.headers.get('authorization');
    if (cookie) headers.set('cookie', cookie);
    if (authorization) headers.set('authorization', authorization);

    const res = await fetch(`${BACKEND}/api/v1/auth/refresh`, {
      method: 'POST',
      headers,
      body,
      cache: 'no-store',
    });

    const raw = await res.text();
    let data: any = {};
    try { data = JSON.parse(raw); } catch { data = { detail: raw }; }

    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    const response = NextResponse.json({
      token_type: data.token_type,
      user: data.user,
      session_id: data.session_id,
      token_family: data.token_family,
    }, { status: res.status });

    if (data.access_token && data.refresh_token) {
      setSessionCookies(response, data.access_token, data.refresh_token);
    }

    return response;
  } catch (e) {
    return NextResponse.json(
      { success: false, message: 'Backend refresh unavailable', error: String(e) },
      { status: 503 }
    );
  }
}
