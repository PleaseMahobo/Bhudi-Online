'use client';

import { useMemo, useState } from 'react';
import { Check, Copy, Download, Monitor, Server, Terminal } from 'lucide-react';

const DEFAULT_SERVER =
  (typeof process !== 'undefined' &&
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, '')) ||
  'https://bhudi-online-production.up.railway.app';

const EXE_RELEASE =
  'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-setup-latest/bhudi-agent-setup.exe';

type OsKey = 'exe' | 'windows' | 'linux' | 'macos';

const OS_OPTIONS: { key: OsKey; label: string }[] = [
  { key: 'exe', label: 'Windows (.exe)' },
  { key: 'windows', label: 'Windows (.ps1)' },
  { key: 'linux', label: 'Linux (.sh)' },
  { key: 'macos', label: 'macOS (.sh)' },
];

function origin(): string {
  if (typeof window === 'undefined') return '';
  return window.location.origin;
}

export default function AgentInstallerPanel({
  serverUrl = DEFAULT_SERVER,
  compact = false,
}: {
  serverUrl?: string;
  compact?: boolean;
}) {
  const [os, setOs] = useState<OsKey>('exe');
  const [copied, setCopied] = useState<'link' | 'cmd' | null>(null);

  const cleanServer = serverUrl.replace(/\/+$/, '').replace(/\/api\/v1$/i, '');

  const downloadHref = useMemo(() => {
    if (os === 'exe') {
      // Prefer app proxy (local file or redirect to GitHub release EXE)
      return '/api/agent/download?os=exe&server=' + encodeURIComponent(cleanServer);
    }
    const q = new URLSearchParams({ os: os, server: cleanServer });
    return '/api/agent/download?' + q.toString();
  }, [os, cleanServer]);

  const oneLiner = useMemo(() => {
    if (os === 'exe') {
      return 'Download bhudi-agent-setup.exe and run as Administrator';
    }
    const url = origin() + downloadHref + '&inline=1';
    if (os === 'windows') {
      return 'irm "' + url + '" | iex';
    }
    return 'curl -fsSL "' + url + '" | bash';
  }, [os, downloadHref]);

  const fullDownloadUrl =
    os === 'exe' ? origin() + downloadHref || EXE_RELEASE : origin() + downloadHref;

  const copy = async (kind: 'link' | 'cmd', text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      setCopied(null);
    }
  };

  const pad = compact ? 'p-4' : 'p-5';

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Server size={16} className="text-indigo-600" />
          Install agent
        </div>
        <span className="text-xs text-slate-500">EXE · Scripts</span>
      </header>

      <div className={'space-y-4 ' + pad}>
        <p className="text-sm text-slate-600 leading-relaxed">
          <strong>Recommended:</strong> download the Windows <span className="font-mono text-xs">.exe</span> setup,
          run it as Administrator, and the agent installs and enrolls automatically.
        </p>

        <div className="flex flex-wrap gap-2">
          {OS_OPTIONS.map((opt) => {
            const active = os === opt.key;
            const cls = active
              ? 'border-indigo-300 bg-indigo-50 text-indigo-800'
              : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50';
            return (
              <button
                key={opt.key}
                type="button"
                onClick={() => setOs(opt.key)}
                className={
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition ' +
                  cls
                }
              >
                <Monitor size={12} />
                {opt.label}
              </button>
            );
          })}
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <a
            href={downloadHref}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            <Download size={16} />
            {os === 'exe' ? 'Download bhudi-agent-setup.exe' : 'Download installer'}
          </a>
          <button
            type="button"
            onClick={() => copy('link', fullDownloadUrl || EXE_RELEASE)}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {copied === 'link' ? <Check size={16} /> : <Copy size={16} />}
            {copied === 'link' ? 'Copied link' : 'Copy link'}
          </button>
        </div>

        {os === 'exe' ? (
          <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-600 leading-relaxed">
            <p className="font-semibold text-slate-800">After download</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4">
              <li>Right-click <span className="font-mono">bhudi-agent-setup.exe</span> → Run as administrator</li>
              <li>Allow the installer to download the agent package and create the startup task</li>
              <li>Confirm the device appears under Devices / Assets</li>
            </ol>
            <p className="mt-2 text-slate-500">Requires Python 3.10+ on the PC (python.org, Add to PATH).</p>
            <p className="mt-1">
              Direct release link:{' '}
              <a className="text-indigo-600 hover:underline break-all" href={EXE_RELEASE}>
                {EXE_RELEASE}
              </a>
            </p>
          </div>
        ) : (
          <div>
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-500">
              <Terminal size={12} />
              One-line install
            </div>
            <div className="flex gap-2">
              <pre className="flex-1 overflow-x-auto rounded-xl bg-slate-900 px-3 py-2.5 text-[11px] leading-relaxed text-slate-200">
                {oneLiner}
              </pre>
              <button
                type="button"
                onClick={() => copy('cmd', oneLiner)}
                className="shrink-0 rounded-xl border border-slate-200 px-3 text-slate-600 hover:bg-slate-50"
                title="Copy command"
              >
                {copied === 'cmd' ? <Check size={16} /> : <Copy size={16} />}
              </button>
            </div>
          </div>
        )}

        <p className="text-[11px] text-slate-400">
          Server: <span className="font-mono text-slate-500">{cleanServer}</span>
        </p>
      </div>
    </section>
  );
}
