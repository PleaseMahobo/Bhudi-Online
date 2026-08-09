import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import path from 'path';

/**
 * Serves Bhudi agent installers as downloadable attachments.
 *
 * Query:
 *   os=windows|linux|macos|bat  (default windows)
 *   server=<backend base URL>   optional — baked into the script
 *
 * Examples:
 *   /api/agent/download?os=windows
 *   /api/agent/download?os=linux&server=https://api.example.com
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const os = (searchParams.get('os') || 'windows').toLowerCase();
  const server =
    searchParams.get('server') ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BHUDI_SERVER_URL ||
    'https://bhudi-online-production.up.railway.app';

  const cleanServer = server.replace(/\/+$/, '').replace(/\/api\/v1$/i, '');

  // agent/ lives at repo root; from frontend/ cwd on Vercel the file may not exist.
  // Prefer reading from process.cwd()/../agent, then embed fallbacks.
  const candidates: Record<string, { file: string; filename: string; type: string }> = {
    windows: { file: 'install.ps1', filename: 'bhudi-agent-install.ps1', type: 'text/plain; charset=utf-8' },
    ps1: { file: 'install.ps1', filename: 'bhudi-agent-install.ps1', type: 'text/plain; charset=utf-8' },
    bat: { file: 'install.bat', filename: 'bhudi-agent-install.bat', type: 'application/x-bat' },
    linux: { file: 'install.sh', filename: 'bhudi-agent-install.sh', type: 'text/x-shellscript; charset=utf-8' },
    macos: { file: 'install.sh', filename: 'bhudi-agent-install.sh', type: 'text/x-shellscript; charset=utf-8' },
    sh: { file: 'install.sh', filename: 'bhudi-agent-install.sh', type: 'text/x-shellscript; charset=utf-8' },
  };

  const meta = candidates[os] || candidates.windows;

  let body: string | null = null;
  const roots = [
    path.join(process.cwd(), '..', 'agent'),
    path.join(process.cwd(), 'agent'),
    path.join(process.cwd(), '..', '..', 'agent'),
  ];

  for (const root of roots) {
    try {
      body = await readFile(path.join(root, meta.file), 'utf8');
      break;
    } catch {
      /* try next */
    }
  }

  if (!body) {
    body = FALLBACK[meta.file] || FALLBACK['install.ps1'];
  }

  // Bake server URL into common placeholders / defaults
  body = body
    .replace(
      /https:\/\/bhudi-online-production\.up\.railway\.app/g,
      cleanServer
    )
    .replace(
      /\$ServerUrl = "https:\/\/bhudi-online-production\.up\.railway\.app"/g,
      `$ServerUrl = "${cleanServer}"`
    );

  // For PowerShell one-liner consumers, if ?inline=1 return without attachment
  const inline = searchParams.get('inline') === '1';

  const headers: Record<string, string> = {
    'Content-Type': meta.type,
    'Cache-Control': 'no-store',
    'X-Bhudi-Server': cleanServer,
  };
  if (!inline) {
    headers['Content-Disposition'] = `attachment; filename="${meta.filename}"`;
  }

  return new NextResponse(body, { status: 200, headers });
}

/** Embedded fallbacks so Vercel (frontend-only root) still serves installers */
const FALLBACK: Record<string, string> = {
  'install.ps1': `# Bhudi Agent Windows installer (embedded fallback)
# Full script ships in repo agent/install.ps1 — this fallback bootstraps from GitHub.
$ErrorActionPreference = "Stop"
$ServerUrl = $env:BHUDI_SERVER_URL
if (-not $ServerUrl) { $ServerUrl = "https://bhudi-online-production.up.railway.app" }
$ServerUrl = $ServerUrl.TrimEnd("/")
$zip = "$env:TEMP\bhudi-main.zip"
$dest = "$env:TEMP\bhudi-src"
Write-Host "[Bhudi] Downloading installer sources..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Expand-Archive $zip $dest -Force
$ps1 = Get-ChildItem -Path $dest -Recurse -Filter install.ps1 | Where-Object { $_.Directory.Name -eq "agent" } | Select-Object -First 1
if (-not $ps1) { throw "agent/install.ps1 not found in archive" }
& $ps1.FullName -ServerUrl $ServerUrl -StartNow
`,
  'install.sh': `#!/usr/bin/env bash
set -euo pipefail
SERVER_URL=""${BHUDI_SERVER_URL:-https://bhudi-online-production.up.railway.app}""
SERVER_URL=""${SERVER_URL%/}""
TMP="$(mktemp -d)"
curl -fsSL "https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip" -o "$TMP/repo.zip"
unzip -q "$TMP/repo.zip" -d "$TMP"
PS1="$(find "$TMP" -path '*/agent/install.sh' | head -1)"
chmod +x "$PS1"
exec "$PS1" --server-url "$SERVER_URL"
`,
  'install.bat': `@echo off
echo [Bhudi] Fetching install.ps1...
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm 'https://raw.githubusercontent.com/PleaseMahobo/Bhudi-Online/main/agent/install.ps1' -OutFile '%TEMP%\\bhudi-install.ps1'; & '%TEMP%\\bhudi-install.ps1'"
pause
`,
};
