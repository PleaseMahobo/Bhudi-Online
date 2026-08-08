'use client';

import React from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { AppShell } from '@/shared/components/AppShell';
import AIAssistant from '@/shared/layout/AIAssistant';
import { Activity, ExternalLink, ShieldCheck, Ticket } from 'lucide-react';

function DashboardWorkspaceBar() {
  return (
    <div className="mb-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Operations live</span>
          </div>
          <p className="mt-1 text-sm text-slate-500">Your at-a-glance workspace for devices, service health, alerts, and security.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/assets" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"><Activity size={14} /> Devices</Link>
          <Link href="/itsm" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"><Ticket size={14} /> Tickets</Link>
          <Link href="/endpoint-security" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"><ShieldCheck size={14} /> Security</Link>
        </div>
      </div>
      <div className="grid grid-cols-2 border-t border-slate-100 sm:grid-cols-4">
        {[
          ['Workspace', 'Production'],
          ['Refresh', '30 sec'],
          ['Coverage', 'RMM + ITSM'],
          ['AI', 'Available'],
        ].map(([label, value], index) => (
          <div key={label} className={`px-5 py-3 ${index > 0 ? 'border-l border-slate-100' : ''}`}>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
            <p className="mt-0.5 text-xs font-semibold text-slate-700">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ModuleShell({
  title,
  subtitle,
  children,
  showAI = true,
}: {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  showAI?: boolean;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [loading, user, router]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-600">Loading…</div>;
  }

  return (
    <AppShell title={title}>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1600px] p-4 sm:p-6">
          {(title || subtitle) && (
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                {title && <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>}
                {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
              </div>
              {title === 'Dashboard' && <Link href="/reporting" className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-500">View reports <ExternalLink size={12} /></Link>}
            </div>
          )}
          {title === 'Dashboard' && <DashboardWorkspaceBar />}
          {children}
        </div>
      </main>
      {showAI && <AIAssistant />}
    </AppShell>
  );
}

export function Panel({ title, actions, children }: { title: string; actions?: React.ReactNode; children: React.ReactNode }) {
  return <div className="mb-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="mb-4 flex items-center justify-between gap-4"><h2 className="text-base font-semibold text-slate-900">{title}</h2>{actions}</div>{children}</div>;
}

export function Err({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>;
}

export function Btn({ onClick, children, variant = 'primary' }: { onClick?: () => void; children: React.ReactNode; variant?: 'primary' | 'ghost' }) {
  const cls = variant === 'primary' ? 'bg-indigo-600 hover:bg-indigo-500 text-white' : 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200';
  return <button type="button" onClick={onClick} className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${cls}`}>{children}</button>;
}

export function DataTable({ columns, rows, empty = 'No data' }: { columns: string[]; rows: (string | number | null | undefined)[][]; empty?: string }) {
  if (!rows.length) return <p className="text-sm text-slate-500">{empty}</p>;
  return <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b border-slate-200 text-left text-slate-500">{columns.map((c) => <th key={c} className="py-2 pr-4 font-medium">{c}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i} className="border-b border-slate-100 text-slate-700">{row.map((cell, j) => <td key={j} className="max-w-xs truncate py-2.5 pr-4">{cell ?? '—'}</td>)}</tr>)}</tbody></table></div>;
}
