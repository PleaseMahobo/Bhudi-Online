'use client';

import React from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { useRouter } from 'next/navigation';
import AppSidebar from '@/shared/layout/AppSidebar';
import Header from '@/shared/layout/Header';
import AIAssistant from '@/shared/layout/AIAssistant';

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
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-600">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <AppSidebar />

      {/* Main column — offset by sidebar width (w-64 = 16rem) */}
      <div className="flex flex-1 flex-col min-w-0 ml-64">
        <Header />

        <main className="flex-1 overflow-y-auto">
          <div className="p-6 max-w-[1600px] mx-auto">
            {(title || subtitle) && (
              <div className="mb-6">
                {title && (
                  <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
                )}
                {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
              </div>
            )}
            {children}
          </div>
        </main>
      </div>

      {showAI && <AIAssistant />}
    </div>
  );
}

export function Panel({
  title,
  actions,
  children,
}: {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 mb-5 shadow-sm">
      <div className="flex items-center justify-between gap-4 mb-4">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {actions}
      </div>
      {children}
    </div>
  );
}

export function Err({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {error}
    </div>
  );
}

export function Btn({
  onClick,
  children,
  variant = 'primary',
}: {
  onClick?: () => void;
  children: React.ReactNode;
  variant?: 'primary' | 'ghost';
}) {
  const cls =
    variant === 'primary'
      ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
      : 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200';
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${cls}`}
    >
      {children}
    </button>
  );
}

export function DataTable({
  columns,
  rows,
  empty = 'No data',
}: {
  columns: string[];
  rows: (string | number | null | undefined)[][];
  empty?: string;
}) {
  if (!rows.length) {
    return <p className="text-sm text-slate-500">{empty}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500 border-b border-slate-200">
            {columns.map((c) => (
              <th key={c} className="py-2 pr-4 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-100 text-slate-700">
              {row.map((cell, j) => (
                <td key={j} className="py-2.5 pr-4 max-w-xs truncate">
                  {cell ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
