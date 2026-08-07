import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

export async function GET(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization') || '';
    const res = await fetch(`${BACKEND}/api/v1/devices/`, {
      headers: auth ? { Authorization: auth } : {},
      cache: 'no-store',
    });
    const data = await res.json().catch(() => ({ devices: [] }));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ devices: [] }, { status: 503 });
  }
}
