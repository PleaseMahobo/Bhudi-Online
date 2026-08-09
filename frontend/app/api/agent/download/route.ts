import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import path from 'path';

const DEFAULT_SERVER = 'https://bhudi-online-production.up.railway.app';
const REPO_ZIP =
  'https://github.com/PleaseMahobo/Bhudi-Online/archive/refs/heads/main.zip';
const REPO_PS1 =
  'https://raw.githubusercontent.com/PleaseMahobo/Bhudi-Online/main/agent/install.ps1';

/** Published by .github/workflows/build-agent-setup.yml */
const EXE_RELEASE_URL =
  'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-setup-latest/bhudi-agent-setup.exe';

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
      'echo [Bhudi] Opening Windows EXE installer download...',
      'start "" "' + EXE_RELEASE_URL + '"',
      'echo If the browser download fails, get bhudi-agent-setup.exe from:',
      'echo ' + EXE_RELEASE_URL,
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

/**
 * Serves agent installers.
 *
 * os=exe|windows-exe  → redirect to published Windows setup EXE (preferred)
 * os=windows|ps1|bat|linux|macos → script download
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const os = (searchParams.get('os') || 'exe').toLowerCase();
  const server =
    searchParams.get('server') ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BHUDI_SERVER_URL ||
    DEFAULT_SERVER;
  const cleanServer = normalizeServer(server);

  // Prefer real Windows EXE installer
  if (os === 'exe' || os === 'windows-exe' || os === 'msi') {
    const localCandidates = [
      path.join(process.cwd(), 'public', 'downloads', 'bhudi-agent-setup.exe'),
      path.join(process.cwd(), '..', 'agent', 'dist', 'bhudi-agent-setup.exe'),
      path.join(process.cwd(), '..', 'agent', 'cmd', 'bhudi-agent-setup', 'bhudi-agent-setup.exe'),
    ];
    for (const p of localCandidates) {
      try {
        const buf = await readFile(p);
        return new NextResponse(buf, {
          status: 200,
          headers: {
            'Content-Type': 'application/vnd.microsoft.portable-executable',
            'Content-Disposition': 'attachment; filename="bhudi-agent-setup.exe"',
            'Cache-Control': 'no-store',
            'X-Bhudi-Server': cleanServer,
          },
        });
      } catch {
        /* try next / fall through to release URL */
      }
    }

    // Published by GitHub Actions (tag: agent-setup-latest)
    const url = new URL(EXE_RELEASE_URL);
    return NextResponse.redirect(url.toString(), 302);
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
