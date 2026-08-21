'use client';

import React, { useState } from 'react';
import AppSidebar from '@/shared/layout/AppSidebar';
import AppTopBar from '@/shared/layout/AppTopBar';

export default function AppShell({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-50">
      <AppSidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col md:ml-64">
        <AppTopBar title={title} onMenuClick={() => setMobileOpen(true)} />
        {children}
      </div>
    </div>
  );
}
