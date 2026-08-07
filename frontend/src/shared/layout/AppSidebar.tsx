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
  /** When true, only exact pathname match counts as active */
  exact?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, exact: true },
  { label: 'Devices', href: '/dashboard#devices', icon: Server },
  { label: 'Alert Engine', href: '/alert-engine', icon: Bell },
  { label: 'Commands', href: '/commands', icon: Terminal },
  { label: 'Endpoint Security', href: '/endpoint-security', icon: Shield },
  { label: 'Software Deploy', href: '/software-deployment', icon: Download },
  { label: 'Assets', href: '/assets', icon: Boxes },
  { label: 'ITSM', href: '/itsm', icon: Ticket },
  { label: 'Packages', href: '/software-deployment#packages', icon: Package },
  { label: 'Settings', href: '/dashboard#settings', icon: Settings },
];

function pathWithoutHash(href: string): string {
  return href.split('#')[0] || href;
}

function isActivePath(pathname: string | null, item: NavItem): boolean {
  if (!pathname) return false;
  const base = pathWithoutHash(item.href);

  // Hash-only secondary items never steal active from primary routes
  if (item.href.includes('#')) {
    return false;
  }

  if (item.exact) {
    return pathname === base;
  }

  if (pathname === base) return true;
  return pathname.startsWith(`${base}/`);
}

const LINK_BASE =
  'group relative flex items-center gap-3 px-4 py-3 rounded-2xl text-sm ' +
  'transform-gpu will-change-transform ' +
  'transition-[background-color,color,box-shadow,transform,opacity] duration-300 ease-out ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-[#111827]';

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
        <div
          className={
            'w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-600 rounded-2xl ' +
            'flex items-center justify-center font-bold text-3xl shadow-lg shadow-sky-500/30 ' +
            'transition-transform duration-300 ease-out hover:scale-105 hover:rotate-3'
          }
        >
          B
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tighter text-white">BHUDI</h1>
          <p className="text-sky-400 text-sm -mt-1">RMM PLATFORM</p>
        </div>
      </div>

      <div className="mb-8">
        <p className="text-xs text-zinc-500 uppercase tracking-wider">Logged in as</p>
        <p className="font-medium text-zinc-200 truncate">{user?.email || '—'}</p>
      </div>

      <nav className="space-y-1.5 pb-24" aria-label="Main">
        {NAV_ITEMS.map((item) => {
          const active = isActivePath(pathname, item);
          const Icon = item.icon;

          return (
            <Link
              key={`${item.href}-${item.label}`}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={
                active
                  ? [
                      LINK_BASE,
                      'font-semibold text-white',
                      'bg-gradient-to-r from-sky-600 to-sky-500',
                      'shadow-lg shadow-sky-500/25 ring-1 ring-sky-300/40',
                      'hover:shadow-sky-400/40 hover:brightness-110',
                      'active:scale-[0.98]',
                    ].join(' ')
                  : [
                      LINK_BASE,
                      'font-medium text-zinc-400',
                      'hover:text-zinc-50 hover:bg-zinc-800/90',
                      'hover:translate-x-1 hover:shadow-md hover:shadow-black/20',
                      'active:scale-[0.98] active:translate-x-0.5',
                    ].join(' ')
              }
            >
              {/* Active / hover indicator bar */}
              <span
                className={
                  active
                    ? [
                        'absolute left-0 top-1/2 -translate-y-1/2',
                        'h-8 w-1 rounded-r-full bg-white',
                        'shadow-[0_0_12px_rgba(255,255,255,0.6)]',
                        'transition-all duration-300 ease-out',
                      ].join(' ')
                    : [
                        'absolute left-0 top-1/2 -translate-y-1/2',
                        'h-0 w-1 rounded-r-full bg-sky-400 opacity-0',
                        'group-hover:h-5 group-hover:opacity-60',
                        'transition-all duration-300 ease-out',
                      ].join(' ')
                }
                aria-hidden
              />

              <span
                className={
                  active
                    ? [
                        'flex h-8 w-8 items-center justify-center rounded-xl',
                        'bg-white/15 text-white',
                        'transition-all duration-300 ease-out',
                        'group-hover:bg-white/25 group-hover:scale-110',
                      ].join(' ')
                    : [
                        'flex h-8 w-8 items-center justify-center rounded-xl',
                        'bg-zinc-800/60 text-zinc-400',
                        'transition-all duration-300 ease-out',
                        'group-hover:text-sky-300 group-hover:bg-zinc-800',
                        'group-hover:scale-110 group-hover:rotate-3',
                      ].join(' ')
                }
              >
                <Icon
                  size={17}
                  strokeWidth={active ? 2.25 : 1.75}
                  className="transition-transform duration-300 ease-out group-hover:scale-110"
                />
              </span>

              <span className="truncate transition-colors duration-300">{item.label}</span>

              {active ? (
                <span
                  className={
                    'ml-auto h-1.5 w-1.5 rounded-full bg-white/90 ' +
                    'shadow-[0_0_8px_rgba(255,255,255,0.8)] ' +
                    'transition-transform duration-300 group-hover:scale-125'
                  }
                  aria-hidden
                />
              ) : (
                <span
                  className={
                    'ml-auto h-1.5 w-1.5 rounded-full bg-sky-400/0 ' +
                    'opacity-0 scale-50 ' +
                    'group-hover:opacity-70 group-hover:scale-100 group-hover:bg-sky-400/80 ' +
                    'transition-all duration-300 ease-out'
                  }
                  aria-hidden
                />
              )}
            </Link>
          );
        })}
      </nav>

      <button
        type="button"
        onClick={handleLogout}
        className={
          'absolute bottom-8 left-6 right-6 flex items-center gap-3 rounded-2xl px-4 py-3 text-sm ' +
          'text-red-400 hover:text-red-300 hover:bg-red-950/40 ' +
          'transform-gpu transition-all duration-300 ease-out ' +
          'hover:translate-x-1 active:scale-[0.98] ' +
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400/50'
        }
      >
        <LogOut
          size={20}
          className="transition-transform duration-300 ease-out group-hover:translate-x-0.5"
        />
        Sign Out
      </button>
    </div>
  );
}
