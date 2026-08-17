'use client';

import { useMemo, useState } from 'react';
import { Check, Copy, Download, Loader2, Monitor, Server, ShieldCheck, Terminal } from 'lucide-react';

const DEFAULT_SERVER =
  (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, '')) ||
  'https://generous-presence-production-b237.up.railway.app';
const RELEASE = 'https://github.com/PleaseMahobo/Bhudi-Online/releases/download/agent-native-latest';
const SETUP = `${RELEASE}/BhudiAgent-Setup.exe`;

type OsKey = 'exe' | 'linux' | 'linux-arm64' | 'macos' | 'macos-intel';
const OS_OPTIONS: { key: OsKey; label: string; file: string }[] = [
  { key: 'exe', label: 'Windows Installer (.exe)', file: 'BhudiAgent-Setup.exe' },
  { key: 'linux', label: 'Linux x64', file: 'bhudi-agent-linux-amd64' },
  { key: 'linux-arm64', label: 'Linux ARM64', file: 'bhudi-agent-linux-arm64' },
  { key: 'macos', label: 'macOS Apple Silicon', file: 'bhudi-agent-darwin-arm64' },
  { key: 'macos-intel', label: 'macOS Intel', file: 'bhudi-agent-darwin-amd64' },
];

export default function AgentInstallerPanel({ serverUrl = DEFAULT_SERVER, compact = false }: { serverUrl?: string; compact?: boolean }) {
  const [os, setOs] = useState<OsKey>('exe');
  const [token, setToken] = useState('');
  const [expires, setExpires] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState('');
  const [error, setError] = useState('');
  const cleanServer = serverUrl.replace(/\/$/, '');
  const meta = OS_OPTIONS.find((o) => o.key === os) || OS_OPTIONS[0];

  async function generateToken() {
    setLoading(true); setError('');
    try {
      const res = await fetch('/api/agent/enrollment-token', { method: 'POST', cache: 'no-store' });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Could not generate enrollment token');
      setToken(String(data.token || ''));
      setExpires(String(data.expires_at || ''));
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not generate enrollment token'); }
    finally { setLoading(false); }
  }

  const installCmd = useMemo(() => {
    if (!token) return 'Generate a customer enrollment token first.';
    switch (os) {
      case 'exe': return `BhudiAgent-Setup.exe /SERVER="${cleanServer}" /TOKEN="${token}"`;
      case 'linux': return `chmod +x bhudi-agent-linux-amd64\nsudo ./bhudi-agent-linux-amd64 install -server ${cleanServer} -enrollment-token ${token}`;
      case 'linux-arm64': return `chmod +x bhudi-agent-linux-arm64\nsudo ./bhudi-agent-linux-arm64 install -server ${cleanServer} -enrollment-token ${token}`;
      case 'macos': return `chmod +x bhudi-agent-darwin-arm64\n./bhudi-agent-darwin-arm64 install -server ${cleanServer} -enrollment-token ${token}`;
      case 'macos-intel': return `chmod +x bhudi-agent-darwin-amd64\n./bhudi-agent-darwin-amd64 install -server ${cleanServer} -enrollment-token ${token}`;
    }
  }, [cleanServer, os, token]);

  function copy(kind: string, text: string) {
    void navigator.clipboard.writeText(text).then(() => { setCopied(kind); setTimeout(() => setCopied(''), 2000); });
  }

  function downloadInstaller() {
    const a = document.createElement('a');
    a.href = SETUP;
    a.download = 'BhudiAgent-Setup.exe';
    a.click();
  }

  function downloadBootstrap() {
    if (!token) return;
    const script = `@echo off\r\nset "BHUDI_SERVER_URL=${cleanServer}"\r\nset "BHUDI_ENROLLMENT_TOKEN=${token}"\r\nPowerShell -NoProfile -ExecutionPolicy Bypass -Command "$u='${SETUP}'; $p=Join-Path $env:TEMP 'BhudiAgent-Setup.exe'; Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p; Start-Process $p -ArgumentList '/SERVER=${cleanServer}','/TOKEN=${token}' -Verb RunAs -Wait"\r\n`;
    const blob = new Blob([script], { type: 'application/octet-stream' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'BhudiAgent-Customer-Installer.cmd'; a.click(); URL.revokeObjectURL(url);
  }

  return (
    <section className={compact ? 'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm' : 'rounded-2xl border border-slate-200 bg-white p-6 shadow-sm'}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="flex items-center gap-2 text-lg font-bold text-slate-900"><Server size={20} className="text-indigo-600" />Customer agent installer</h2><p className="mt-1 text-sm text-slate-500">Generate a tenant-bound, single-use enrollment package. No Python required.</p></div>
        <ShieldCheck size={20} className="text-emerald-500" />
      </div>

      <div className="mt-5 space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{OS_OPTIONS.map((o) => <button key={o.key} type="button" onClick={() => setOs(o.key)} className={'rounded-xl border px-3 py-2.5 text-left text-sm ' + (os === o.key ? 'border-indigo-300 bg-indigo-50 text-indigo-900' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50')}><span className="font-medium">{o.label}</span><span className="mt-0.5 block text-[11px] text-slate-500">{o.file}</span></button>)}</div>

        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void generateToken()} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60">{loading ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}Generate customer installer</button>
          <button type="button" onClick={downloadInstaller} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Download size={16} />Download Windows Installer</button>
          {token && <button type="button" onClick={downloadBootstrap} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Download size={16} />Download customer .cmd</button>}
        </div>

        {error && <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        {token && <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-xs text-emerald-900"><p className="font-semibold">Customer token generated</p><p className="mt-1">Single-use and tenant-bound. {expires ? `Expires ${new Date(expires).toLocaleString()}.` : ''} It is consumed during first enrollment and then removed from the endpoint.</p><div className="mt-2 flex gap-2"><code className="min-w-0 flex-1 overflow-hidden text-ellipsis rounded bg-white px-2 py-1 font-mono">{token}</code><button type="button" onClick={() => copy('token', token)} className="rounded border border-emerald-200 bg-white px-2">{copied === 'token' ? <Check size={14} /> : <Copy size={14} />}</button></div></div>}

        <div><div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-500"><Terminal size={12} />Install command</div><div className="flex gap-2"><pre className="flex-1 overflow-x-auto rounded-xl bg-slate-900 px-3 py-2.5 text-[11px] leading-relaxed text-slate-200">{installCmd}</pre><button type="button" disabled={!token} onClick={() => copy('cmd', installCmd)} className="shrink-0 rounded-xl border border-slate-200 px-3 text-slate-600 disabled:opacity-40">{copied === 'cmd' ? <Check size={16} /> : <Copy size={16} />}</button></div></div>

        <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-600"><p className="font-semibold text-slate-800">Windows</p><ol className="mt-2 list-decimal space-y-1 pl-4"><li>Generate a customer enrollment token.</li><li>Download <code>BhudiAgent-Setup.exe</code>.</li><li>Run the installer as Administrator.</li><li>Enter the server URL and customer token in the installer, or use the generated command for silent/scripted deployment.</li><li>The installer registers the Windows service and enrolls the endpoint to this customer only.</li></ol></div>
        <p className="text-[11px] text-slate-400"><Monitor size={12} className="mr-1 inline" />Server: <span className="font-mono text-slate-500">{cleanServer}</span> · zero endpoint runtime dependencies</p>
      </div>
    </section>
  );
}
