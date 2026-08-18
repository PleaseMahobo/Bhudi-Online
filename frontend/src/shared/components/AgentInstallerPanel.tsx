'use client';

import { useMemo, useState } from 'react';
import { Check, Copy, Download, Monitor, Server, Terminal } from 'lucide-react';

const DEFAULT_SERVER =
  (typeof process !== 'undefined' &&
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, '')) ||
  'https://bhudi-online-production-b237.up.railway.app';

type OsKey = 'exe' | 'msi' | 'linux' | 'linux-arm64' | 'macos' | 'macos-intel';

const OS_OPTIONS: { key: OsKey; label: string; file: string; hint?: string }[] = [
  { key: 'exe', label: 'Windows (.exe)', file: 'BhudiAgent-Setup.exe', hint: 'Customer-specific · Recommended' },
  { key: 'msi', label: 'Windows (.msi)', file: 'bhudi-agent-setup.msi', hint: 'For Intune / Group Policy' },
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
  const [os, setOs] = useState<OsKey>('exe');
  const [copied, setCopied] = useState('');

  const cleanServer = (serverUrl || DEFAULT_SERVER).replace(/\/$/, '');
  const meta = OS_OPTIONS.find((o) => o.key === os) || OS_OPTIONS[0];
  const downloadHref = '/api/agent/download?os=' + os;

  const installCmd = useMemo(() => {
    switch (os) {
      case 'msi':
        return `msiexec /i bhudi-agent-setup.msi /qn SERVERURL="${cleanServer}"\n# Use the customer-specific EXE for automatic enrollment.`;
      case 'exe':
        return 'Download and run BhudiAgent-Setup.exe as Administrator. No token or command is required.';
      case 'linux':
        return `chmod +x bhudi-agent-linux-amd64\nsudo ./bhudi-agent-linux-amd64 install -server ${cleanServer}`;
      case 'linux-arm64':
        return `chmod +x bhudi-agent-linux-arm64\nsudo ./bhudi-agent-linux-arm64 install -server ${cleanServer}`;
      case 'macos':
        return `chmod +x bhudi-agent-darwin-arm64\n./bhudi-agent-darwin-arm64 install -server ${cleanServer}`;
      case 'macos-intel':
        return `chmod +x bhudi-agent-darwin-amd64\n./bhudi-agent-darwin-amd64 install -server ${cleanServer}`;
      default:
        return '';
    }
  }, [os, cleanServer]);

  function copy(kind: string, text: string) {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(kind);
      setTimeout(() => setCopied(''), 2000);
    });
  }

  return (
    <section className={compact ? 'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm' : 'rounded-2xl border border-slate-200 bg-white p-6 shadow-sm'}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <Server size={20} className="text-indigo-600" />
            Download customer agent
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Your download is bound to this customer account and enrolls automatically. No token entry is required.
          </p>
        </div>
        <Monitor size={18} className="text-slate-300" />
      </div>

      <div className="mt-5 space-y-4">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Platform</p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {OS_OPTIONS.map((o) => (
              <button key={o.key} type="button" onClick={() => setOs(o.key)} className={'rounded-xl border px-3 py-2.5 text-left text-sm transition ' + (os === o.key ? 'border-indigo-300 bg-indigo-50 text-indigo-900' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50')}>
                <span className="font-medium">{o.label}</span>
                {o.hint && <span className="mt-0.5 block text-[11px] font-normal text-slate-500">{o.hint}</span>}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <a href={downloadHref} className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500">
            <Download size={16} />
            Download {meta.file}
          </a>
          <button type="button" onClick={() => copy('link', typeof window !== 'undefined' ? window.location.origin + downloadHref : downloadHref)} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
            {copied === 'link' ? <Check size={16} /> : <Copy size={16} />}
            {copied === 'link' ? 'Copied' : 'Copy link'}
          </button>
        </div>

        <div className="rounded-xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-xs leading-relaxed text-emerald-900">
          <p className="font-semibold">Windows EXE — automatic enrollment</p>
          <p className="mt-1">Each download receives a single-use enrollment bootstrap for your current customer tenant. The token is embedded in the installer and is never requested from the end user.</p>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs leading-relaxed text-slate-600">
          <p className="font-semibold text-slate-800">After download</p>
          <ol className="mt-2 list-decimal space-y-1 pl-4">
            {os === 'msi' && <li>Deploy the MSI with Intune / GPO. For automatic customer enrollment, use the EXE download.</li>}
            {os === 'exe' && <><li>Right-click <strong>BhudiAgent-Setup.exe</strong> → Run as administrator.</li><li>Follow the installer prompts. <strong>No enrollment token is requested.</strong></li><li>The Windows service installs automatically and the endpoint enrolls into this customer account.</li></>}
            {os.startsWith('linux') && <><li>Make the binary executable, then run <span className="font-mono">install</span> with sudo.</li><li>Registers a systemd service and starts the agent.</li></>}
            {os.startsWith('macos') && <><li>Make the binary executable, then run <span className="font-mono">install</span>.</li><li>Creates a LaunchAgent and starts the agent.</li></>}
          </ol>
        </div>

        <div>
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-500"><Terminal size={12} /> Install command</div>
          <div className="flex gap-2">
            <pre className="flex-1 overflow-x-auto rounded-xl bg-slate-900 px-3 py-2.5 text-[11px] leading-relaxed text-slate-200">{installCmd}</pre>
            <button type="button" onClick={() => copy('cmd', installCmd)} className="shrink-0 rounded-xl border border-slate-200 px-3 text-slate-600 hover:bg-slate-50">{copied === 'cmd' ? <Check size={16} /> : <Copy size={16} />}</button>
          </div>
        </div>

        <p className="text-[11px] text-slate-400">Server: <span className="font-mono text-slate-500">{cleanServer}</span> · Windows EXE downloads are tenant-bound and single-use.</p>
      </div>
    </section>
  );
}
