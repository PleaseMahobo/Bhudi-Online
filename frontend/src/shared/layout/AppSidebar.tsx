'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { motion, type Transition } from 'framer-motion';
import {
  LayoutDashboard,
  Monitor,
  Users,
  Ticket,
  Zap,
  ScreenShare,
  Printer,
  Shield,
  Package,
  Boxes,
  Terminal,
  BarChart3,
  CreditCard,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  exact?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, exact: true },
  { label: 'Devices', href: '/assets', icon: Monitor },
  { label: 'Customers', href: '/msp', icon: Users },
  { label: 'Tickets', href: '/itsm', icon: Ticket },
  { label: 'Automation', href: '/commands', icon: Zap },
  { label: 'Remote Access', href: '/commands', icon: ScreenShare },
  { label: 'Print Management', href: '/assets', icon: Printer },
  { label: 'Endpoint Security', href: '/endpoint-security', icon: Shield },
  { label: 'Patching', href: '/software-deployment', icon: Package },
  { label: 'Software', href: '/software-deployment', icon: Boxes },
  { label: 'Scripts', href: '/commands', icon: Terminal },
  { label: 'Reports', href: '/reporting', icon: BarChart3 },
  { label: 'Billing', href: '/billing', icon: CreditCard },
  { label: 'Settings', href: '/compliance', icon: Settings },
];

const SPRING_SNAPPY: Transition = {
  type: 'spring',
  stiffness: 420,
  damping: 28,
  mass: 0.6,
};

const SPRING_SOFT: Transition = {
  type: 'spring',
  stiffness: 260,
  damping: 22,
  mass: 0.8,
};

function isActivePath(pathname: string | null, item: NavItem): boolean {
  if (!pathname) return false;
  if (item.exact) return pathname === item.href;
  if (pathname === item.href) return true;
  return pathname.startsWith(`${item.href}/`);
}

const MotionLink = motion.create(Link);

export default function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      router.push('/login');
    }
  };

  return (
    <aside
      className={`flex flex-col h-screen bg-[#0F172A] text-slate-300 border-r border-slate-800 transition-all duration-300 fixed z-40 ${
        collapsed ? 'w-[72px]' : 'w-64'
      }`}
    >
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-slate-800 shrink-0">
        {!collapsed ? (
          <Link href="/dashboard" className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white text-sm shrink-0">
              B
            </div>
            <div className="min-w-0">
              <span className="text-base font-semibold text-white tracking-tight block truncate">
                Bhudi
              </span>
              <span className="text-[10px] text-indigo-400 uppercase tracking-wider">
                IT Operations
              </span>
            </div>
          </Link>
        ) : (
          <Link
            href="/dashboard"
            className="w-8 h-8 mx-auto rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white text-sm"
          >
            B
          </Link>
        )}
      </div>

      {/* User (when expanded) */}
      {!collapsed && (
        <div className="px-4 py-3 border-b border-slate-800/80">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider">Logged in as</p>
          <p className="text-sm font-medium text-slate-200 truncate">{user?.email || '—'}</p>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5" aria-label="Main">
        {NAV_ITEMS.map((item, index) => {
          const active = isActivePath(pathname, item);
          const Icon = item.icon;

          return (
            <MotionLink
              key={`${item.href}-${item.label}`}
              href={item.href}
              title={collapsed ? item.label : undefined}
              aria-current={active ? 'page' : undefined}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ ...SPRING_SOFT, delay: index * 0.015 }}
              whileHover={active ? { scale: 1.01 } : { scale: 1.01, x: 2 }}
              whileTap={{ scale: 0.98 }}
              className={
                active
                  ? 'group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold text-indigo-300 bg-indigo-600/20'
                  : 'group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800/90'
              }
            >
              {active && (
                <motion.span
                  layoutId="sidebar-active-bar"
                  className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-0.5 rounded-r-full bg-indigo-400"
                  transition={SPRING_SNAPPY}
                  aria-hidden
                />
              )}

              <span
                className={
                  active
                    ? 'flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600/30 text-indigo-300 shrink-0'
                    : 'flex h-7 w-7 items-center justify-center rounded-md text-slate-500 group-hover:text-indigo-300 shrink-0'
                }
              >
                <Icon size={17} strokeWidth={active ? 2.25 : 1.75} />
              </span>

              {!collapsed && <span className="truncate">{item.label}</span>}
            </MotionLink>
          );
        })}
      </nav>

      {/* Footer actions */}
      <div className="p-2 border-t border-slate-800 space-y-1 shrink-0">
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span>Collapse</span>
            </>
          )}
        </button>

        <button
          type="button"
          onClick={handleLogout}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-950/40 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
          title="Sign out"
        >
          <LogOut size={17} />
          {!collapsed && <span>Sign Out</span>}
        </button>
      </div>
    </aside>
  );
}
