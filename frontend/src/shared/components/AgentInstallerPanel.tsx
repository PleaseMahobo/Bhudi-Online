'use client';

import { useMemo, useState } from 'react';
import { Check, Copy, Download, Monitor, Server, Terminal } from 'lucide-react';

const DEFAULT_SERVER =
  (typeof process !== 'undefined' &&
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, '')) ||
  'https://bhudi-online-production.up.railway.app';

const RELEASE =
  'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest';

type OsKey =
  | 'msi'
  | 'exe'
  | 'linux'
  | 'linux-arm64'
  | 'macos'
  | 'macos-intel';

const OS_OPTIONS: { key: OsKey; label: string; file: string }[] = [
  { key: 'msi', label: 'Windows (.msi)', file: 'bhudi-agent-setup.msi' },
  { key: 'exe', label: 'Windows (.exe)', file: 'bhudi-agent.exe' },
  { key: 'linux', label: 'Linux x64', file: 'bhudi-agent-linux-amd64' },
  { key: 'linux-arm64', label: 'Linux ARM64', file: 'bhudi-agent-linux-arm64' },
  { key: 'macos', label: 'macOS Apple Silicon', file: 'bhudi-agent-darwin-arm64' },
  { key: 'macos-intel', label: 'macOS Intel', file: 'bhudi-agent-darwin-amd64' },
];

export default function AgentInstallerPanel({
  serverUrl = DEFAULT_SERVER,
  compact = false,
}: {
  serverUrl?: string;
  compact?: boolean;
}) {
  const [os, setOs] = useState<OsKey>('msi');
  const [copied, setCopied] = useState<'link' | 'cmd' | null>(null);

  const cleanServer = serverUrl.replace(/\/+$/, '').replace(/\/api\/v1$/i, '');
  const meta = OS_OPTIONS.find((o) => o.key === os) || OS_OPTIONS[0];
  const downloadHref = '/api/agent/download?os=' + os;
  const directUrl = RELEASE + '/' + meta.file;

  const installCmd = useMemo(() => {
    if (os === 'msi') {
      return 'msiexec /i bhudi-agent-setup.msi SERVERURL=' + cleanServer + ' /qb';
    }
    if (os === 'exe') {
      return 'bhudi-agent.exe install -server ' + cleanServer;
    }
    if (os.startsWith('linux')) {
      return (
        'chmod +x ' +
        meta.file +
        ' && sudo ./' +
        meta.file +
        ' install -server ' +
        cleanServer
      );
    }
    return 'chmod +x ' + meta.file + ' && ./' + meta.file + ' install -server ' + cleanServer;
  }, [os, cleanServer, meta.file]);

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
        <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700">
          No Python required
        </span>
      </header>

      <div className={'space-y-4 ' + pad}>
        <p className="text-sm text-slate-600 leading-relaxed">
          Native standalone agent for ordinary Windows, Linux, and macOS endpoints. One binary — no
          runtime to pre-install on user machines.
        </p>

        <div className="flex flex-wrap gap-2">
          {OS_OPTIONS.map((opt) => {
            const active = os === opt.key;
            return (
              <button
                key={opt.key}
                type="button"
                onClick={() => setOs(opt.key)}
                className={
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition ' +
                  (active
                    ? 'border-indigo-300 bg-indigo-50 text-indigo-800'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50')
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
            Download {meta.file}
          </a>
          <button
            type="button"
            onClick={() => copy('link', directUrl)}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {copied === 'link' ? <Check size={16} /> : <Copy size={16} />}
            {copied === 'link' ? 'Copied' : 'Copy link'}
          </button>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-600 leading-relaxed">
          <p className="font-semibold text-slate-800">After download</p>
          <ol className="mt-2 list-decimal space-y-1 pl-4">
            {os === 'msi' && (
              <>
                <li>Deploy with Intune / GPO or double-click the MSI</li>
                <li>Agent installs and starts automatically (no Python)</li>
              </>
            )}
            {os === 'exe' && (
              <>
                <li>Right-click → Run as administrator (recommended)</li>
                <li>
                  Or run:{' '}
                  <span className="font-mono">bhudi-agent.exe install -server …</span>
                </li>
              </>
            )}
            {os.startsWith('linux') && (
              <>
                <li>
                  <span className="font-mono">chmod +x</span> the file, then run{' '}
                  <span className="font-mono">install</span> (sudo recommended)
                </li>
                <li>Creates a systemd user service and starts the agent</li>
              </>
            )}
            {os.startsWith('macos') && (
              <>
                <li>
                  <span className="font-mono">chmod +x</span>, then run{' '}
                  <span className="font-mono">install</span>
                </li>
                <li>Creates a LaunchAgent and starts the agent</li>
              </>
            )}
          </ol>
        </div>

        <div>
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Terminal size={12} />
            Install command
          </div>
          <div className="flex gap-2">
            <pre className="flex-1 overflow-x-auto rounded-xl bg-slate-900 px-3 py-2.5 text-[11px] leading-relaxed text-slate-200">
              {installCmd}
            </pre>
            <button
              type="button"
              onClick={() => copy('cmd', installCmd)}
              className="shrink-0 rounded-xl border border-slate-200 px-3 text-slate-600 hover:bg-slate-50"
            >
              {copied === 'cmd' ? <Check size={16} /> : <Copy size={16} />}
            </button>
          </div>
        </div>

        <p className="text-[11px] text-slate-400">
          Server: <span className="font-mono text-slate-500">{cleanServer}</span>
          {' · '}Native agent v2 — zero endpoint runtime dependencies
        </p>
      </div>
    </section>
  );
}
