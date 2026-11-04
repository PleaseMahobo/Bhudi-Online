import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
)
  .replace(/\/$/, '')
  .replace(/\/api\/v1$/, '');

/** Proxy POST /api/auth/register → FastAPI /api/v1/auth/register. */
export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const res = await fetch(`${BACKEND}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body,
      cache: 'no-store',
    });

    const raw = await res.text();
    let data: unknown = {};
    try {
      data = JSON.parse(raw);
    } catch {
      data = { detail: raw || res.statusText };
    }

    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json(
      { detail: 'Backend registration unavailable', error: String(e) },
      { status: 503 },
    );
  }
}
