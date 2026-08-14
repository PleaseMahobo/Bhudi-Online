// frontend/app/api/[...path]/route.ts
// Catch-all proxy → FastAPI backend (single source of truth)
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
)
  .replace(/\/$/, '')
  .replace(/\/api\/v1$/, '');

export async function GET(request: NextRequest) { return proxyRequest(request); }
export async function POST(request: NextRequest) { return proxyRequest(request); }
export async function PUT(request: NextRequest) { return proxyRequest(request); }
export async function PATCH(request: NextRequest) { return proxyRequest(request); }
export async function DELETE(request: NextRequest) { return proxyRequest(request); }

function forwardSetCookies(upstream: Response, response: NextResponse) {
  const cookies = upstream.headers.getSetCookie?.() ?? [];
  for (const cookie of cookies) response.headers.append('set-cookie', cookie);
}

async function proxyRequest(request: NextRequest) {
  try {
    let pathname = request.nextUrl.pathname;
    if (!pathname.startsWith('/api/v1/') && pathname.startsWith('/api/')) {
      pathname = `/api/v1/${pathname.slice('/api/'.length)}`;
    }

    const target = `${BACKEND_URL}${pathname}${request.nextUrl.search}`;
    const headers = new Headers();
    for (const name of ['content-type', 'authorization', 'cookie', 'accept']) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }

    const init: RequestInit = { method: request.method, headers, cache: 'no-store' };
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      init.body = await request.arrayBuffer();
    }

    const upstream = await fetch(target, init);
    const data = await upstream.arrayBuffer();
    const response = new NextResponse(data, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') || 'application/json',
      },
    });

    // Forward FastAPI Set-Cookie headers so refresh/login/logout cookie
    // rotation reaches the browser through the same-origin proxy.
    forwardSetCookies(upstream, response);
    return response;
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend connection failed', detail: String(error) },
      { status: 503 }
    );
  }
}
