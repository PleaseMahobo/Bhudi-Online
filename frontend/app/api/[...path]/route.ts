// frontend/app/api/[...path]/route.ts
// Catch-all proxy → FastAPI backend (single source of truth)
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
).replace(/\/$/, '');

export async function GET(request: NextRequest) {
  return proxyRequest(request);
}

export async function POST(request: NextRequest) {
  return proxyRequest(request);
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request);
}

export async function PATCH(request: NextRequest) {
  return proxyRequest(request);
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request);
}

async function proxyRequest(request: NextRequest) {
  try {
    // /api/auth/login → backend /api/v1/auth/login
    // /api/v1/devices → backend /api/v1/devices (no double prefix)
    let pathname = request.nextUrl.pathname;
    if (pathname.startsWith('/api/v1/')) {
      // already versioned
    } else if (pathname.startsWith('/api/')) {
      pathname = `/api/v1/${pathname.slice('/api/'.length)}`;
    }

    const target = `${BACKEND_URL}${pathname}${request.nextUrl.search}`;

    const headers = new Headers();
    const contentType = request.headers.get('content-type');
    if (contentType) headers.set('content-type', contentType);
    const auth = request.headers.get('authorization');
    if (auth) headers.set('authorization', auth);
    const accept = request.headers.get('accept');
    if (accept) headers.set('accept', accept);

    const init: RequestInit = {
      method: request.method,
      headers,
      cache: 'no-store',
    };

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      init.body = await request.arrayBuffer();
    }

    const response = await fetch(target, init);
    const data = await response.arrayBuffer();

    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type':
          response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend connection failed', detail: String(error) },
      { status: 503 }
    );
  }
}
