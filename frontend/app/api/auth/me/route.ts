import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
)
  .replace(/\/$/, '')
  .replace(/\/api\/v1$/, '');

export async function GET(request: NextRequest) {
  try {
    const token = request.cookies.get('access_token')?.value;
    const auth = request.headers.get('authorization') || (token ? `Bearer ${token}` : '');

    if (!auth) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    // The portal now authenticates with Supabase. Do not send the Supabase
    // access token to the legacy Bhudi-JWT /auth/me endpoint; that endpoint
    // expects Bhudi-issued JWT claims and will reject a valid Supabase JWT.
    const res = await fetch(`${BACKEND}/api/v1/supabase-auth/me`, {
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
