// frontend/app/api/[...path]/route.ts
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bhudi-online-production.up.railway.app';

export async function GET(request: NextRequest) {
  return proxyRequest(request);
}

export async function POST(request: NextRequest) {
  return proxyRequest(request);
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request);
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request);
}

async function proxyRequest(request: NextRequest) {
  try {
    const path = request.nextUrl.pathname.replace('/api/', '');
    const url = new URL(path, BACKEND_URL);
    url.search = request.nextUrl.search;

    const body = request.body ? await request.text() : undefined;

    const response = await fetch(url.toString(), {
      method: request.method,
      headers: {
        'Content-Type': request.headers.get('Content-Type') || 'application/json',
        ...Object.fromEntries(request.headers.entries()),
      },
      body: body,
      cache: 'no-store',
    });

    const data = await response.text();
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend connection failed' },
      { status: 503 }
    );
  }
}
