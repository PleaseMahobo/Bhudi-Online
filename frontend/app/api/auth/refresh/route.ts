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

    const data = await res.text();
    const response = new NextResponse(data, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('Content-Type') || 'application/json',
      },
    });
    forwardSetCookies(res, response);
    return response;
  } catch (e) {
    return NextResponse.json(
      { success: false, message: 'Backend refresh unavailable', error: String(e) },
      { status: 503 }
    );
  }
}
