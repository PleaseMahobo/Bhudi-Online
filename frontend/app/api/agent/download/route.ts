import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import path from 'path';

const DEFAULT_SERVER = 'https://bhudi-online-production.up.railway.app';
const REPO_ZIP =
  'https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip';
const REPO_PS1 =
  'https://raw.githubusercontent.com/PleaseMahobo/Bhudi-Online/main/agent/install.ps1';

const EXE_RELEASE_URL =
  'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-setup-latest/bhudi-agent-setup.exe';
const MSI_RELEASE_URL =
  'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-setup-latest/bhudi-agent-setup.msi';

type InstallerMeta = {
  file: string;
  filename: string;
  type: string;
};

const CANDIDATES: Record<string, InstallerMeta> = {
  windows: {
    file: 'install.ps1',
    filename: 'bhudi-agent-install.ps1',
    type: 'text/plain; charset=utf-8',
  },
  ps1: {
    file: 'install.ps1',
    filename: 'bhudi-agent-install.ps1',
    type: 'text/plain; charset=utf-8',
  },
  bat: {
    file: 'install.bat',
    filename: 'bhudi-agent-install.bat',
    type: 'application/x-bat',
  },
  linux: {
    file: 'install.sh',
    filename: 'bhudi-agent-install.sh',
    type: 'text/x-shellscript; charset=utf-8',
  },
  macos: {
    file: 'install.sh',
    filename: 'bhudi-agent-install.sh',
    type: 'text/x-shellscript; charset=utf-8',
  },
  sh: {
    file: 'install.sh',
    filename: 'bhudi-agent-install.sh',
    type: 'text/x-shellscript; charset=utf-8',
  },
};

function lines(parts: string[]): string {
  return parts.join('\n');
}

function buildFallbacks(): Record<string, string> {
  return {
    'install.ps1': lines([
      '# Bhudi Agent Windows installer (embedded fallback)',
      '$ErrorActionPreference = "Stop"',
      '$ServerUrl = $env:BHUDI_SERVER_URL',
      'if (-not $ServerUrl) { $ServerUrl = "' + DEFAULT_SERVER + '" }',
      '$ServerUrl = $ServerUrl.TrimEnd("/")',
      '$zip = "$env:TEMP\\bhudi-main.zip"',
      '$dest = "$env:TEMP\\bhudi-src"',
      'Write-Host "[Bhudi] Downloading installer sources..." -ForegroundColor Cyan',
      'Invoke-WebRequest -Uri "' + REPO_ZIP + '" -OutFile $zip -UseBasicParsing',
      'if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }',
      'Expand-Archive $zip $dest -Force',
      '$ps1 = Get-ChildItem -Path $dest -Recurse -Filter install.ps1 | Where-Object { $_.Directory.Name -eq "agent" } | Select-Object -First 1',
      'if (-not $ps1) { throw "agent/install.ps1 not found in archive" }',
      '& $ps1.FullName -ServerUrl $ServerUrl -StartNow',
      '',
    ]),
    'install.sh': lines([
      '#!/usr/bin/env bash',
      'set -euo pipefail',
      'SERVER_URL="${BHUDI_SERVER_URL:-' + DEFAULT_SERVER + '}"',
      'SERVER_URL="${SERVER_URL%/}"',
      'TMP="$(mktemp -d)"',
      'curl -fsSL "' + REPO_ZIP + '" -o "$TMP/repo.zip"',
      'unzip -q "$TMP/repo.zip" -d "$TMP"',
      'PS1="$(find "$TMP" -path \'*/agent/install.sh\' | head -1)"',
      'chmod +x "$PS1"',
      'exec "$PS1" --server-url "$SERVER_URL"',
      '',
    ]),
    'install.bat': lines([
      '@echo off',
      'echo [Bhudi] Opening MSI installer download...',
      'start "" "' + MSI_RELEASE_URL + '"',
      'echo Direct MSI: ' + MSI_RELEASE_URL,
      'echo Direct EXE: ' + EXE_RELEASE_URL,
      'pause',
      '',
    ]),
  };
}

const FALLBACK = buildFallbacks();

function normalizeServer(raw: string): string {
  return raw.replace(/\/+$/, '').replace(/\/api\/v1$/i, '');
}

function bakeServer(script: string, cleanServer: string): string {
  return script.split(DEFAULT_SERVER).join(cleanServer);
}

async function tryServeLocalBinary(
  names: string[],
  contentType: string,
  downloadName: string,
  cleanServer: string
): Promise<NextResponse | null> {
  const roots = [
    path.join(process.cwd(), 'public', 'downloads'),
    path.join(process.cwd(), '..', 'agent', 'msi'),
    path.join(process.cwd(), '..', 'agent', 'dist'),
    path.join(process.cwd(), '..', 'agent', 'cmd', 'bhudi-agent-setup'),
  ];
  for (const root of roots) {
    for (const name of names) {
      try {
        const buf = await readFile(path.join(root, name));
        return new NextResponse(buf, {
          status: 200,
          headers: {
            'Content-Type': contentType,
            'Content-Disposition': 'attachment; filename="' + downloadName + '"',
            'Cache-Control': 'no-store',
            'X-Bhudi-Server': cleanServer,
          },
        });
      } catch {
        /* continue */
      }
    }
  }
  return null;
}

/**
 * Serves agent installers.
 *
 * os=msi              → Windows MSI (enterprise)
 * os=exe|windows-exe  → Windows setup EXE
 * os=windows|ps1|...  → scripts
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const os = (searchParams.get('os') || 'msi').toLowerCase();
  const server =
    searchParams.get('server') ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BHUDI_SERVER_URL ||
    DEFAULT_SERVER;
  const cleanServer = normalizeServer(server);

  if (os === 'msi') {
    const local = await tryServeLocalBinary(
      ['bhudi-agent-setup.msi'],
      'application/x-msi',
      'bhudi-agent-setup.msi',
      cleanServer
    );
    if (local) return local;
    return NextResponse.redirect(MSI_RELEASE_URL, 302);
  }

  if (os === 'exe' || os === 'windows-exe') {
    const local = await tryServeLocalBinary(
      ['bhudi-agent-setup.exe'],
      'application/vnd.microsoft.portable-executable',
      'bhudi-agent-setup.exe',
      cleanServer
    );
    if (local) return local;
    return NextResponse.redirect(EXE_RELEASE_URL, 302);
  }

  const meta = CANDIDATES[os] || CANDIDATES.windows;
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
  body = bakeServer(body, cleanServer);

  const inline = searchParams.get('inline') === '1';
  const headers: Record<string, string> = {
    'Content-Type': meta.type,
    'Cache-Control': 'no-store',
    'X-Bhudi-Server': cleanServer,
  };
  if (!inline) {
    headers['Content-Disposition'] = 'attachment; filename="' + meta.filename + '"';
  }

  return new NextResponse(body, { status: 200, headers });
}
