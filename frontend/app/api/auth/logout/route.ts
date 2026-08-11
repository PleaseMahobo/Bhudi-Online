import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

export async function POST(request: NextRequest) {
  try {
    const headers = new Headers();
    const cookie = request.headers.get('cookie');
    const auth = request.headers.get('authorization');
    if (cookie) headers.set('cookie', cookie);
    if (auth) headers.set('authorization', auth);

    const res = await fetch(`${BACKEND}/api/v1/auth/logout`, {
      method: 'POST',
      headers,
      cache: 'no-store',
    });

    const data = await res.text();
    const response = new NextResponse(data || JSON.stringify({ success: true }), {
      status: res.ok ? res.status : 200,
      headers: {
        'Content-Type': res.headers.get('Content-Type') || 'application/json',
      },
    });

    // Clear the browser-side session cookies even if the backend response
    // cannot be forwarded because the session has already expired.
    response.cookies.set('access_token', '', { maxAge: 0, path: '/' });
    response.cookies.set('refresh_token', '', { maxAge: 0, path: '/' });
    return response;
  } catch {
    const response = NextResponse.json({ success: true, message: 'Logged out locally' });
    response.cookies.set('access_token', '', { maxAge: 0, path: '/' });
    response.cookies.set('refresh_token', '', { maxAge: 0, path: '/' });
    return response;
  }
}
