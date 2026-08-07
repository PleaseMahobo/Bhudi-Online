'use client';

import React from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import { useRouter } from 'next/navigation';
import AppSidebar from '@/shared/layout/AppSidebar';

export default function ModuleShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0f1c] flex items-center justify-center text-white">
        Loading…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-white flex">
      <AppSidebar />
      <div className="flex-1 ml-72 p-10">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-sky-300 to-blue-400 bg-clip-text text-transparent">
              {title}
            </h1>
            {subtitle && <p className="text-sky-400/90 mt-1">{subtitle}</p>}
          </div>
          {children}
        </div>
      </div>
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
    <div className="bg-zinc-900 border border-zinc-700 rounded-3xl p-6 mb-6">
      <div className="flex items-center justify-between gap-4 mb-4">
        <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
        {actions}
      </div>
      {children}
    </div>
  );
}

export function Err({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="mb-4 rounded-xl border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-300">
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
      ? 'bg-sky-600 hover:bg-sky-500 text-white'
      : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-600';
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${cls}`}
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
    return <p className="text-sm text-zinc-500">{empty}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            {columns.map((c) => (
              <th key={c} className="py-2 pr-4 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-zinc-800/60 text-zinc-200">
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
