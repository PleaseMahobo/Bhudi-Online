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

async function resolveAuth(request: NextRequest): Promise<string> {
  const current = getAuth(request);
  if (current) return current;

  // Recover an expired/missing access token from the portal's HttpOnly refresh
  // cookie before proxying tenant-scoped API requests.
  const refreshToken = request.cookies.get('refresh_token')?.value;
  if (!refreshToken) return '';

  const refresh = await fetch(`${BACKEND}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: `refresh_token=${refreshToken}` },
    cache: 'no-store',
  });
  if (!refresh.ok) return '';
  const data = await refresh.json().catch(() => null);
  return data?.access_token ? `Bearer ${data.access_token}` : '';
}

async function proxy(request: NextRequest, path: string[] = []) {
  const auth = await resolveAuth(request);
  if (!auth) {
    return NextResponse.json({ detail: 'Authentication credentials missing' }, { status: 401 });
  }

  const suffix = path.length ? `/${path.join('/')}` : '';
  // Reuse the authenticated same-origin boundary for tenant-scoped device
  // operations. Browser requests must not call Railway directly because the
  // HttpOnly Bhudi session cookie is scoped to the portal origin.
  const upstream = path[0] === 'devices'
    ? `${BACKEND}/api/v1/devices${path.slice(1).length ? `/${path.slice(1).join('/')}` : ''}`
    : `${BACKEND}/api/v1/auth/tenant-context${suffix}`;
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

type RouteContext = { params: Promise<{ path?: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return proxy(request, path);
}
