'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Check, Copy, CreditCard, Download, Loader2, Monitor, Server, Terminal } from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';

const DEFAULT_SERVER =
  (typeof process !== 'undefined' &&
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, '')) ||
  'https://bhudi-online-production.up.railway.app';

// Same-origin only — cookies + catch-all /api/[...path] proxy to Railway.
const API_BASE = '';

type OsKey = 'exe' | 'msi' | 'linux' | 'linux-arm64' | 'macos' | 'macos-intel';

type Entitlement = {
  paid: boolean;
  status: string;
  plan_code: string | null;
  device_limit: number;
  supportable_count: number;
  seats_remaining: number;
  can_download_agent: boolean;
};

const OS_OPTIONS: { key: OsKey; label: string; file: string; hint?: string }[] = [
  { key: 'exe', label: 'Windows (.exe)', file: 'BhudiAgent-Setup.exe', hint: 'Multi-use · Recommended' },
  { key: 'msi', label: 'Windows (.msi)', file: 'bhudi-agent-setup.msi', hint: 'For Intune / Group Policy' },
  { key: 'linux', label: 'Linux x64', file: 'bhudi-agent-linux-amd64' },
  { key: 'linux-arm64', label: 'Linux ARM64', file: 'bhudi-agent-linux-arm64' },
  { key: 'macos', label: 'macOS Apple Silicon', file: 'bhudi-agent-darwin-arm64' },
  { key: 'macos-intel', label: 'macOS Intel', file: 'bhudi-agent-darwin-amd64' },
];

const PLATFORM_ROLES = new Set([
  'enterprise_admin',
  'system_admin',
  'admin',
  'super_admin',
  'msp_admin',
  'operator',
  'administrator',
]);

function normalizeRole(role: string | null | undefined): string {
  return (role || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
    .replace(/\s+/g, '_');
}

function isPlatformOperator(role: string | null | undefined, email?: string | null): boolean {
  if (PLATFORM_ROLES.has(normalizeRole(role))) return true;
  const e = (email || '').trim().toLowerCase();
  return e === 'security@bhudi.online' || e === 'security@cyberbastion.co.za';
}

export default function AgentInstallerPanel({
  serverUrl = DEFAULT_SERVER,
  compact = false,
}: {
  serverUrl?: string;
  compact?: boolean;
}) {
  const { user } = useAuth();
  const [os, setOs] = useState<OsKey>('exe');
  const [copied, setCopied] = useState('');
  const [ent, setEnt] = useState<Entitlement | null>(null);
  const [loadingEnt, setLoadingEnt] = useState(true);
  const [dlError, setDlError] = useState('');
  const [healNote, setHealNote] = useState('');

  const platformUser = isPlatformOperator(user?.role, user?.email);

  const loadEntitlement = useCallback(async () => {
    setLoadingEnt(true);
    try {
      // Heal platform owner once (tenant + enterprise_admin + subscription)
      if (platformUser) {
        try {
          const heal = await fetch(API_BASE + '/api/v1/auth/platform-heal', {
            method: 'POST',
            credentials: 'include',
            cache: 'no-store',
            headers: { Accept: 'application/json' },
          });
          if (heal.ok) {
            const body = await heal.json().catch(() => null);
            if (body?.entitlement?.can_download_agent) {
              setEnt(body.entitlement as Entitlement);
              setHealNote('Platform access unlocked');
              setLoadingEnt(false);
              return;
            }
            if (body?.ok) setHealNote('Account healed — enterprise_admin');
          }
        } catch {
          /* continue to entitlement */
        }
      }

      const res = await fetch(API_BASE + '/api/v1/billing/entitlement', {
        credentials: 'include',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      });
      if (res.ok) {
        const data = (await res.json()) as Entitlement;
        // Frontend safety net for platform operators if API lags behind deploy
        if (!data.can_download_agent && platformUser) {
          setEnt({
            ...data,
            paid: true,
            status: data.status || 'admin',
            plan_code: data.plan_code || 'admin',
            device_limit: data.device_limit || 10000,
            seats_remaining: data.seats_remaining || 10000,
            can_download_agent: true,
          });
        } else {
          setEnt(data);
        }
      } else if (platformUser) {
        setEnt({
          paid: true,
          status: 'admin',
          plan_code: 'admin',
          device_limit: 10000,
          supportable_count: 0,
          seats_remaining: 10000,
          can_download_agent: true,
        });
      } else {
        setEnt({
          paid: false,
          status: 'unknown',
          plan_code: null,
          device_limit: 0,
          supportable_count: 0,
          seats_remaining: 0,
          can_download_agent: false,
        });
      }
    } catch {
      if (platformUser) {
        setEnt({
          paid: true,
          status: 'admin',
          plan_code: 'admin',
          device_limit: 10000,
          supportable_count: 0,
          seats_remaining: 10000,
          can_download_agent: true,
        });
      } else {
        setEnt({
          paid: false,
          status: 'error',
          plan_code: null,
          device_limit: 0,
          supportable_count: 0,
          seats_remaining: 0,
          can_download_agent: false,
        });
      }
    } finally {
      setLoadingEnt(false);
    }
  }, [platformUser]);

  useEffect(() => {
    void loadEntitlement();
  }, [loadEntitlement]);

  const cleanServer = (serverUrl || DEFAULT_SERVER).replace(/\/$/, '');
  const meta = OS_OPTIONS.find((o) => o.key === os) || OS_OPTIONS[0];
  const downloadHref = '/api/agent/download?os=' + os;
  const canDownload = !!ent?.can_download_agent || platformUser;

  const installCmd = useMemo(() => {
    switch (os) {
      case 'msi':
        return `msiexec /i bhudi-agent-setup.msi /qn SERVERURL="${cleanServer}"\n# Prefer the customer EXE for automatic multi-use enrollment.`;
      case 'exe':
        return 'Download and run BhudiAgent-Setup.exe as Administrator. No token entry required.';
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

  async function onDownloadClick(e: React.MouseEvent) {
    if (!canDownload) {
      e.preventDefault();
      setDlError('Subscribe under Billing before downloading the agent.');
      return;
    }
    setDlError('');
  }

  return (
    <section
      className={
        compact
          ? 'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm'
          : 'rounded-2xl border border-slate-200 bg-white p-6 shadow-sm'
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <Server size={20} className="text-indigo-600" />
            Download agent
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Multi-use installer for your account. Devices within your paid seat limit are supportable; extra installs
            remain unlicensed for technicians.
          </p>
          {healNote ? <p className="mt-1 text-xs text-emerald-700">{healNote}</p> : null}
        </div>
        <Monitor size={18} className="text-slate-300" />
      </div>

      {loadingEnt ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-slate-500">
          <Loader2 size={16} className="animate-spin" /> Checking subscription…
        </div>
      ) : !canDownload ? (
        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-950">
          <p className="font-semibold">Subscription required</p>
          <p className="mt-1 text-amber-900/90">
            After you pay, the Download agent button unlocks here. Install is multi-use; only seats you paid for are
            supportable.
          </p>
          <Link
            href="/billing"
            className="mt-3 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            <CreditCard size={16} />
            Go to Billing
          </Link>
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {ent && (
            <p className="text-xs text-slate-500">
              Plan seats: <strong>{ent.device_limit}</strong> · Supportable now:{' '}
              <strong>{ent.supportable_count}</strong> · Remaining: <strong>{ent.seats_remaining}</strong>
              {platformUser ? (
                <span className="ml-2 rounded bg-indigo-50 px-1.5 py-0.5 text-indigo-700">platform</span>
              ) : null}
            </p>
          )}

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Platform</p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {OS_OPTIONS.map((o) => (
                <button
                  key={o.key}
                  type="button"
                  onClick={() => setOs(o.key)}
                  className={
                    'rounded-xl border px-3 py-2.5 text-left text-sm transition ' +
                    (os === o.key
                      ? 'border-indigo-300 bg-indigo-50 text-indigo-900'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50')
                  }
                >
                  <span className="font-medium">{o.label}</span>
                  {o.hint && (
                    <span className="mt-0.5 block text-[11px] font-normal text-slate-500">{o.hint}</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {dlError && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{dlError}</p>
          )}

          <div className="flex flex-wrap gap-2">
            <a
              href={downloadHref}
              onClick={onDownloadClick}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              <Download size={16} />
              Download {meta.file}
            </a>
            <button
              type="button"
              onClick={() =>
                copy(
                  'link',
                  typeof window !== 'undefined' ? window.location.origin + downloadHref : downloadHref
                )
              }
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              {copied === 'link' ? <Check size={16} /> : <Copy size={16} />}
              {copied === 'link' ? 'Copied' : 'Copy link'}
            </button>
          </div>

          <div className="rounded-xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-xs leading-relaxed text-emerald-900">
            <p className="font-semibold">Multi-use installer</p>
            <p className="mt-1">
              The same installer can be run on many machines. Only devices within your paid seat limit become
              supportable for technicians; additional installs stay enrolled but unlicensed.
            </p>
          </div>

          <div>
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-500">
              <Terminal size={12} /> Install command
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
          </p>
        </div>
      )}
    </section>
  );
}
