import { NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/api/v1/health`, { cache: 'no-store' });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    // Fall back to root health endpoint used by some deploys
    try {
      const res = await fetch(`${BACKEND}/health`, { cache: 'no-store' });
      const data = await res.json();
      return NextResponse.json(data, { status: res.status });
    } catch {
      return NextResponse.json(
        { status: 'error', message: 'Backend unreachable' },
        { status: 503 }
      );
    }
  }
}
