import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
)
  .replace(/\/$/, '')
  .replace(/\/api\/v1$/, '');

function forwardSetCookies(upstream: Response, response: NextResponse) {
  const cookies = upstream.headers.getSetCookie?.() ?? [];
  for (const cookie of cookies) {
    response.headers.append('set-cookie', cookie);
  }
}

/** Proxy POST /api/auth/login → FastAPI /api/v1/auth/login. */
export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const res = await fetch(`${BACKEND}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      cache: 'no-store',
    });

    const data = await res.text();
    const response = new NextResponse(data, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('Content-Type') || 'application/json',
      },
    });

    // FastAPI sets HttpOnly access/refresh cookies. Forward both cookies to
    // the browser so subsequent same-origin requests remain authenticated.
    forwardSetCookies(res, response);
    return response;
  } catch (e) {
    return NextResponse.json(
      { detail: 'Backend login unavailable', error: String(e) },
      { status: 503 }
    );
  }
}
