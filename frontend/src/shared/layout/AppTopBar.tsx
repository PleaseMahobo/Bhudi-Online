'use client';

import React, { useState } from 'react';
import { ChevronDown, HelpCircle, Menu, Sparkles } from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';
import GlobalSearch from '@/shared/layout/GlobalSearch';
import NotificationCenter from '@/shared/layout/NotificationCenter';

export default function AppTopBar({ title, onMenuClick }: { title?: string; onMenuClick?: () => void }) {
  const { user, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const initials = user?.email?.split('@')[0]?.slice(0, 2)?.toUpperCase() || 'U';

  const handleLogout = async () => { await logout(); };

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur md:px-6">
      <button type="button" onClick={onMenuClick} className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 md:hidden" aria-label="Open navigation"><Menu size={20} /></button>
      <div className="hidden min-w-0 md:block md:w-44 lg:w-56"><p className="truncate text-sm font-semibold text-slate-900">{title || 'Workspace'}</p><p className="truncate text-[11px] text-slate-500">IT Operations</p></div>
      <GlobalSearch />
      <div className="ml-auto flex items-center gap-1">
        <button type="button" className="hidden h-9 items-center gap-2 rounded-lg px-3 text-sm font-medium text-indigo-700 hover:bg-indigo-50 lg:inline-flex" title="Ask Bhudi AI"><Sparkles size={16} />Ask Bhudi</button>
        <button type="button" className="hidden h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 sm:inline-flex" aria-label="Help"><HelpCircle size={18} /></button>
        <NotificationCenter />
        <div className="relative ml-1">
          <button type="button" onClick={() => setProfileOpen((value) => !value)} className="flex items-center gap-2 rounded-lg p-1.5 pr-2 hover:bg-slate-100" aria-expanded={profileOpen}>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">{initials}</span>
            <span className="hidden max-w-36 truncate text-left text-xs font-medium text-slate-700 xl:block">{user?.email || 'User'}</span>
            <ChevronDown size={14} className="hidden text-slate-400 xl:block" />
          </button>
          {profileOpen && <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-xl"><div className="border-b border-slate-100 px-3 py-2"><p className="truncate text-sm font-semibold text-slate-900">{user?.email || 'User'}</p><p className="text-xs text-slate-500">Administrator</p></div><button type="button" className="mt-1 w-full rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50">Profile & preferences</button><button type="button" onClick={handleLogout} className="w-full rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50">Sign out</button></div>}
        </div>
      </div>
    </header>
  );
}
