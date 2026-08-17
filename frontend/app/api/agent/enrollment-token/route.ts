import { NextRequest, NextResponse } from 'next/server';

const API = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export async function POST(req: NextRequest) {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  const authorization = req.headers.get('authorization');
  const cookie = req.headers.get('cookie');
  if (authorization) headers.set('authorization', authorization);
  if (cookie) headers.set('cookie', cookie);

  try {
    const upstream = await fetch(`${API}/api/v1/agents/enrollment-token`, {
      method: 'POST',
      headers,
      cache: 'no-store',
    });
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('content-type') || 'application/json' },
    });
  } catch {
    return NextResponse.json({ detail: 'Agent enrollment service unavailable' }, { status: 502 });
  }
}
