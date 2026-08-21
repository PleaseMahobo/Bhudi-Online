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
    const authorization = request.headers.get('authorization');
    const auth = authorization || (token ? `Bearer ${token}` : '');

    if (!auth) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    // After MFA promotion, access_token is a Bhudi-issued application JWT.
    // Resolve it through the canonical Bhudi /auth/me endpoint, not the
    // Supabase identity endpoint (which expects a Supabase access token).
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
