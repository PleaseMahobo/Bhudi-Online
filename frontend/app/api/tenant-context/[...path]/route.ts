import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
)
  .replace(/\/$/, '')
  .replace(/\/api\/v1$/, '');

function getAuth(request: NextRequest): string {
  const authorization = request.headers.get('authorization');
  if (authorization) return authorization;

  const token = request.cookies.get('access_token')?.value;
  return token ? `Bearer ${token}` : '';
}

async function proxy(request: NextRequest, path: string[]) {
  const auth = getAuth(request);
  if (!auth) {
    return NextResponse.json({ detail: 'Authentication credentials missing' }, { status: 401 });
  }

  const upstream = `${BACKEND}/api/v1/auth/tenant-context/${path.join('/')}`;
  const body = request.method === 'GET' || request.method === 'HEAD'
    ? undefined
    : await request.text();

  try {
    const response = await fetch(upstream, {
      method: request.method,
      headers: {
        Authorization: auth,
        ...(body ? { 'Content-Type': request.headers.get('content-type') || 'application/json' } : {}),
        Accept: 'application/json',
      },
      body,
      cache: 'no-store',
    });

    const data = await response.text();
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'application/json',
      },
    });
  } catch (error) {
    return NextResponse.json(
      { detail: `Tenant context backend unavailable: ${String(error)}` },
      { status: 503 },
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxy(request, path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxy(request, path);
}
