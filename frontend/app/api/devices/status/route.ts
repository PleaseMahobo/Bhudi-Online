// frontend/app/api/devices/status/route.ts
import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/devices/status`, { cache: 'no-store' });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ devices: [] }, { status: 503 });
  }
}
