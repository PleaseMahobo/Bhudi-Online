import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

export async function GET(request: NextRequest) {
  try {
    const auth =
      request.headers.get('authorization') ||
      (request.cookies.get('access_token')?.value
        ? `Bearer ${request.cookies.get('access_token')!.value}`
        : '');

    if (!auth) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    const res = await fetch(`${BACKEND}/api/v1/auth/me`, {
      headers: { Authorization: auth },
      cache: 'no-store',
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json({ authenticated: false, ...data }, { status: res.status });
    }
    return NextResponse.json({ authenticated: true, user: data });
  } catch (e) {
    return NextResponse.json(
      { authenticated: false, detail: String(e) },
      { status: 503 }
    );
  }
}
