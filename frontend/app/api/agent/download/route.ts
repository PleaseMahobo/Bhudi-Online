import { NextRequest, NextResponse } from 'next/server';

const RELEASE =
  'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest';
const BASE_SETUP = RELEASE + '/BhudiAgent-Setup.exe';
const MAGIC = Buffer.from('BHUDI_BOOTSTRAP_V1', 'utf8');
const BACKEND_URL = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://bhudi-online-production.up.railway.app'
)
  .replace(/\/$/, '')
  .replace(/\/api\/v1$/, '');

const STATIC_ASSETS: Record<string, { url: string; fallback?: string }> = {
  msi: {
    url: RELEASE + '/bhudi-agent-setup.msi',
    fallback: RELEASE + '/bhudi-agent.exe',
  },
  linux: { url: RELEASE + '/bhudi-agent-linux-amd64' },
  'linux-amd64': { url: RELEASE + '/bhudi-agent-linux-amd64' },
  'linux-arm64': { url: RELEASE + '/bhudi-agent-linux-arm64' },
  macos: { url: RELEASE + '/bhudi-agent-darwin-arm64' },
  darwin: { url: RELEASE + '/bhudi-agent-darwin-arm64' },
  'darwin-arm64': { url: RELEASE + '/bhudi-agent-darwin-arm64' },
  'darwin-amd64': { url: RELEASE + '/bhudi-agent-darwin-amd64' },
  'macos-intel': { url: RELEASE + '/bhudi-agent-darwin-amd64' },
};

function authHeaders(req: NextRequest): Headers {
  const headers = new Headers({ Accept: 'application/json' });
  for (const name of ['authorization', 'cookie']) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }
  return headers;
}

async function customerInstaller(req: NextRequest): Promise<NextResponse> {
  const tokenResponse = await fetch(`${BACKEND_URL}/api/v1/agents/enrollment-token`, {
    method: 'POST',
    headers: authHeaders(req),
    cache: 'no-store',
  });
  if (!tokenResponse.ok) {
    const detail = await tokenResponse.text();
    return NextResponse.json(
      { error: 'Unable to create customer enrollment token', detail },
      { status: tokenResponse.status === 401 ? 401 : 502 }
    );
  }

  const tokenData = (await tokenResponse.json()) as {
    token?: string;
    expires_at?: string;
    tenant_id?: string;
  };
  if (!tokenData.token || !tokenData.tenant_id) {
    return NextResponse.json({ error: 'Invalid enrollment-token response' }, { status: 502 });
  }

  const baseResponse = await fetch(BASE_SETUP, { cache: 'no-store', redirect: 'follow' });
  if (!baseResponse.ok) {
    return NextResponse.json(
      { error: 'Published BhudiAgent-Setup.exe is unavailable' },
      { status: 503 }
    );
  }

  const base = Buffer.from(await baseResponse.arrayBuffer());
  const payload = Buffer.from(
    JSON.stringify({
      server_url: BACKEND_URL,
      enrollment_token: tokenData.token,
      tenant_id: tokenData.tenant_id,
      expires_at: tokenData.expires_at,
    }),
    'utf8'
  );

  // Footer format consumed by the setup EXE:
  // [JSON payload][uint64 little-endian payload length][magic]
  const length = Buffer.alloc(8);
  length.writeBigUInt64LE(BigInt(payload.length));
  const output = Buffer.concat([base, payload, length, MAGIC]);

  return new NextResponse(output as unknown as BodyInit, {
    status: 200,
    headers: {
      'Content-Type': 'application/vnd.microsoft.portable-executable',
      'Content-Disposition': 'attachment; filename="BhudiAgent-Setup.exe"',
      'Cache-Control': 'private, no-store, max-age=0',
      'X-Bhudi-Installer': 'customer-specific',
    },
  });
}

async function staticDownload(os: string): Promise<NextResponse> {
  const asset = STATIC_ASSETS[os] || { url: RELEASE + '/bhudi-agent.exe' };
  let target = asset.url;
  try {
    const res = await fetch(target, { method: 'HEAD', redirect: 'follow' });
    if (!res.ok && asset.fallback) target = asset.fallback;
  } catch {
    if (asset.fallback) target = asset.fallback;
  }
  return NextResponse.redirect(target, 302);
}

export async function GET(req: NextRequest) {
  const os = (new URL(req.url).searchParams.get('os') || 'exe').toLowerCase();
  if (os === 'exe' || os === 'windows' || os === 'windows-exe') {
    return customerInstaller(req);
  }
  return staticDownload(os);
}
