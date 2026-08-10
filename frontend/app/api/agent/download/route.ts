import { NextRequest, NextResponse } from 'next/server';

/**
 * Native agent downloads — redirects to GitHub release assets.
 * No embedded shell scripts / template literals (Turbopack-safe).
 */
const RELEASE =
  'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest';

const ASSETS: Record<string, { url: string; fallback?: string }> = {
  exe: { url: RELEASE + '/bhudi-agent.exe' },
  'windows-exe': { url: RELEASE + '/bhudi-agent.exe' },
  windows: { url: RELEASE + '/bhudi-agent.exe' },
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

async function resolveUrl(url: string, fallback?: string): Promise<string> {
  try {
    const res = await fetch(url, { method: 'HEAD', redirect: 'follow' });
    if (res.ok) return url;
  } catch {
    /* ignore */
  }
  if (fallback) return fallback;
  return url;
}

/** Default: Windows EXE. MSI falls back to EXE if the MSI asset is not published yet. */
export async function GET(req: NextRequest) {
  const os = (new URL(req.url).searchParams.get('os') || 'exe').toLowerCase();
  const asset = ASSETS[os] || ASSETS.exe;
  const target = await resolveUrl(asset.url, asset.fallback);
  const res = NextResponse.redirect(target, 302);
  res.headers.set('Cache-Control', 'public, max-age=60');
  return res;
}
