import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

/** Proxy POST /api/auth/login → FastAPI /api/v1/auth/login */
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
    return new NextResponse(data, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (e) {
    return NextResponse.json(
      { detail: 'Backend login unavailable', error: String(e) },
      { status: 503 }
    );
  }
}
