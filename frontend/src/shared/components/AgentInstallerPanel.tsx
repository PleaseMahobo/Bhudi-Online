'use client';

import { useMemo, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  Monitor,
  Server,
  Terminal,
} from 'lucide-react';

const DEFAULT_SERVER =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, '') ||
  'https://bhudi-online-production.up.railway.app';

type OsKey = 'windows' | 'linux' | 'macos';

const OS_OPTIONS: { key: OsKey; label: string; file: string }[] = [
  { key: 'windows', label: 'Windows (.ps1)', file: 'bhudi-agent-install.ps1' },
  { key: 'linux', label: 'Linux (.sh)', file: 'bhudi-agent-install.sh' },
  { key: 'macos', label: 'macOS (.sh)', file: 'bhudi-agent-install.sh' },
];

export default function AgentInstallerPanel({
  serverUrl = DEFAULT_SERVER,
  compact = false,
}: {
  serverUrl?: string;
  compact?: boolean;
}) {
  const [os, setOs] = useState<OsKey>('windows');
  const [copied, setCopied] = useState<'link' | 'cmd' | null>(null);

  const cleanServer = serverUrl.replace(/\/+$/, '').replace(/\/api\/v1$/i, '');

  const downloadHref = useMemo(() => {
    const q = new URLSearchParams({ os, server: cleanServer });
    return `/api/agent/download?${q.toString()}`;
  }, [os, cleanServer]);

  const oneLiner = useMemo(() => {
    if (os === 'windows') {
      return `irm "${typeof window !== 'undefined' ? window.location.origin : ''}${downloadHref}&inline=1" | iex`;
    }
    return `curl -fsSL "${typeof window !== 'undefined' ? window.location.origin : ''}${downloadHref}&inline=1" | bash`;
  }, [os, downloadHref]);

  const copy = async (kind: 'link' | 'cmd', text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      setCopied(null);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Server size={16} className="text-indigo-600" />
          Install agent
        </div>
        <span className="text-xs text-slate-500">Windows · Linux · macOS</span>
      </header>

      <div className={`space-y-4 ${compact ? 'p-4' : 'p-5'}`}>
        <p className="text-sm text-slate-600 leading-relaxed">
          Download an installer for the target OS, or copy a one-line install command.
          The agent enrolls automatically and appears under Devices.
        </p>

        <div className="flex flex-wrap gap-2">
          {OS_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              type="button"
              onClick={() => setOs(opt.key)}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                os === opt.key
                  ? 'border-indigo-300 bg-indigo-50 text-indigo-800'
                  : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Monitor size={12} />
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <a
            href={downloadHref}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            <Download size={16} />
            Download installer
          </a>
          <button
            type="button"
            onClick={() =>
              copy(
                'link',
                typeof window !== 'undefined'
                  ? `${window.location.origin}${downloadHref}`
                  : downloadHref
              )
            }
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {copied === 'link' ? <Check size={16} /> : <Copy size={16} />}
            {copied === 'link' ? 'Copied link' : 'Copy link'}
          </button>
        </div>

        <div>
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Terminal size={12} />
            One-line install {os === 'windows' ? '(PowerShell as Admin)' : '(terminal)'}
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

        <p className="text-[11px] text-slate-400">
          Server: <span className="font-mono text-slate-500">{cleanServer}</span>
          {' · '}Requires Python 3.10+ on the target device
        </p>
      </div>
    </section>
  );
}
