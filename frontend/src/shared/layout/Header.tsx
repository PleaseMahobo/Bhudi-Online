'use client';

import { useState } from 'react';
import { Search, Bell, User } from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';

export default function Header() {
  const [search, setSearch] = useState('');
  const { user } = useAuth();

  const initials =
    user?.email
      ?.split('@')[0]
      ?.slice(0, 2)
      ?.toUpperCase() || 'U';

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-5 sticky top-0 z-30 shrink-0">
      {/* Search */}
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search devices, tickets, customers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2 ml-4">
        <button
          type="button"
          className="relative p-2 rounded-lg hover:bg-slate-100 transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-5 h-5 text-slate-600" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white" />
        </button>

        <button
          type="button"
          className="flex items-center gap-2 p-1.5 pr-3 rounded-lg hover:bg-slate-100 transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-semibold">
            {initials}
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-sm font-medium text-slate-900 leading-tight truncate max-w-[140px]">
              {user?.email || 'User'}
            </p>
            <p className="text-xs text-slate-500">Admin</p>
          </div>
        </button>
      </div>
    </header>
  );
}
