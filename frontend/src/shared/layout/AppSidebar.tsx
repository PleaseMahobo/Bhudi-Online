'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Server,
  Bell,
  Terminal,
  Shield,
  Package,
  Download,
  Ticket,
  Boxes,
  Settings,
  LogOut,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Devices', href: '/dashboard', icon: Server },
  { label: 'Alert Engine', href: '/alert-engine', icon: Bell },
  { label: 'Commands', href: '/commands', icon: Terminal },
  { label: 'Endpoint Security', href: '/endpoint-security', icon: Shield },
  { label: 'Software Deploy', href: '/software-deployment', icon: Download },
  { label: 'Assets', href: '/assets', icon: Boxes },
  { label: 'ITSM', href: '/itsm', icon: Ticket },
  { label: 'Packages', href: '/software-deployment', icon: Package },
  { label: 'Settings', href: '/dashboard', icon: Settings },
];

export default function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      router.push('/login');
    }
  };

  return (
    <div className="w-72 bg-[#111827] border-r border-[#1e2937] p-6 fixed h-screen overflow-auto z-40">
      <div className="flex items-center gap-3 mb-10">
        <div className="w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-600 rounded-2xl flex items-center justify-center font-bold text-3xl">
          B
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tighter text-white">BHUDI</h1>
          <p className="text-sky-400 text-sm -mt-1">RMM PLATFORM</p>
        </div>
      </div>

      <div className="mb-8">
        <p className="text-xs text-zinc-500">Logged in as</p>
        <p className="font-medium text-zinc-200 truncate">{user?.email || '—'}</p>
      </div>

      <nav className="space-y-1 pb-24">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== '/dashboard' && pathname?.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={`${item.href}-${item.label}`}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-2xl transition-all text-sm ${
                active
                  ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20'
                  : 'hover:bg-zinc-800 text-zinc-300'
              }`}
            >
              <Icon size={18} className={active ? 'text-white' : 'text-zinc-400'} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        type="button"
        onClick={handleLogout}
        className="absolute bottom-8 left-6 right-6 flex items-center gap-3 text-red-400 hover:text-red-300 text-sm"
      >
        <LogOut size={20} /> Sign Out
      </button>
    </div>
  );
}
