'use client';

import React, { useState } from 'react';
import AppSidebar from '@/shared/layout/AppSidebar';
import AppTopBar from '@/shared/layout/AppTopBar';

/**
 * Shell layout:
 * - Sidebar is position:fixed (out of document flow), width 16rem (w-64).
 * - Main column uses a single md:ml-64 so content sits flush next to the rail.
 * - Do NOT use lg:static on the sidebar — that reintroduces a second 16rem gap.
 */
export default function AppShell({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="relative flex h-screen min-h-0 overflow-hidden bg-slate-50">
      <AppSidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <div className="flex min-h-0 min-w-0 w-full flex-1 flex-col md:ml-64">
        <AppTopBar title={title} onMenuClick={() => setMobileOpen(true)} />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  );
}
