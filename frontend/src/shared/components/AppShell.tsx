'use client';

import React, { useState } from 'react';
import AppSidebar from '@/shared/layout/AppSidebar';
import AppTopBar from '@/shared/layout/AppTopBar';

/**
 * In-flow sidebar on md+: takes exactly w-64 in the flex row.
 * No md:ml-64 / fixed dual positioning — that combination caused the empty gap.
 * Mobile: sidebar is an off-canvas overlay (handled inside AppSidebar).
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
    <div className="flex h-screen min-h-0 w-full overflow-hidden bg-slate-50">
      <AppSidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <AppTopBar title={title} onMenuClick={() => setMobileOpen(true)} />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  );
}
