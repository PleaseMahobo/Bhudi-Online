import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

export async function POST(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization') || '';
    const res = await fetch(`${BACKEND}/api/v1/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(auth ? { Authorization: auth } : {}),
      },
      cache: 'no-store',
    });
    const data = await res.text();
    const response = new NextResponse(data || JSON.stringify({ success: true }), {
      status: res.ok ? res.status : 200,
      headers: { 'Content-Type': 'application/json' },
    });
    response.cookies.set('access_token', '', { maxAge: 0, path: '/' });
    return response;
  } catch {
    const response = NextResponse.json({ success: true, message: 'Logged out locally' });
    response.cookies.set('access_token', '', { maxAge: 0, path: '/' });
    return response;
  }
}
