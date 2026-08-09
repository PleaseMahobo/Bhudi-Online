import { NextRequest, NextResponse } from 'next/server';

/** Native agent release assets — no Python on the endpoint. */
const RELEASE = 'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest';

const ASSETS: Record<string, string> = {
  // Windows
  msi: RELEASE + '/bhudi-agent-setup.msi',
  exe: RELEASE + '/bhudi-agent.exe',
  'windows-exe': RELEASE + '/bhudi-agent.exe',
  windows: RELEASE + '/bhudi-agent.exe',
  // Linux
  linux: RELEASE + '/bhudi-agent-linux-amd64',
  'linux-amd64': RELEASE + '/bhudi-agent-linux-amd64',
  'linux-arm64': RELEASE + '/bhudi-agent-linux-arm64',
  // macOS
  macos: RELEASE + '/bhudi-agent-darwin-arm64',
  darwin: RELEASE + '/bhudi-agent-darwin-arm64',
  'darwin-arm64': RELEASE + '/bhudi-agent-darwin-arm64',
  'darwin-amd64': RELEASE + '/bhudi-agent-darwin-amd64',
  'macos-intel': RELEASE + '/bhudi-agent-darwin-amd64',
};

/**
 * Redirects to the published native agent binary/MSI for the requested OS.
 * Query: os=msi|exe|linux|linux-arm64|macos|darwin-amd64|...
 */
export async function GET(req: NextRequest) {
  const os = (new URL(req.url).searchParams.get('os') || 'msi').toLowerCase();
  const target = ASSETS[os] || ASSETS.msi;
  return NextResponse.redirect(target, 302);
}
