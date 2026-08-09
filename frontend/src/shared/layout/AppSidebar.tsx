'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { motion, type Transition } from 'framer-motion';
import {
  Activity,
  BarChart3,
  Boxes,
  ChevronRight,
  CreditCard,
  Download,
  LayoutDashboard,
  LogOut,
  Monitor,
  Package,
  Printer,
  ScreenShare,
  Settings,
  Shield,
  Ticket,
  Terminal,
  Users,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';

type NavItem = { label: string; href: string; icon: LucideIcon; exact?: boolean; badge?: string };

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, exact: true },
  { label: 'Devices', href: '/assets', icon: Monitor },
  { label: 'Download Agent', href: '/agents', icon: Download },
  { label: 'Customers', href: '/msp', icon: Users },
  { label: 'Tickets', href: '/itsm', icon: Ticket, badge: '3' },
  { label: 'Alerts', href: '/alert-engine', icon: Activity },
  { label: 'Automation', href: '/commands', icon: Zap },
  { label: 'Remote Access', href: '/commands', icon: ScreenShare },
  { label: 'Endpoint Security', href: '/endpoint-security', icon: Shield },
  { label: 'Patch Management', href: '/software-deployment', icon: Package },
  { label: 'Software', href: '/software-deployment', icon: Boxes },
  { label: 'Scripts', href: '/commands', icon: Terminal },
  { label: 'Print Management', href: '/assets', icon: Printer },
  { label: 'Reports', href: '/reporting', icon: BarChart3 },
  { label: 'Billing', href: '/billing', icon: CreditCard },
  { label: 'Settings', href: '/compliance', icon: Settings },
];

const SPRING: Transition = { type: 'spring', stiffness: 380, damping: 28, mass: 0.7 };
const MotionLink = motion.create(Link);

function isActivePath(pathname: string | null, item: NavItem) {
  if (!pathname) return false;
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export default function AppSidebar({
  mobileOpen = false,
  onMobileClose,
}: {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      router.push('/login');
      onMobileClose?.();
    }
  };

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onMobileClose}
          className="fixed inset-0 z-40 bg-slate-950/50 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-800 bg-slate-950 text-slate-100 transition-transform duration-200 lg:static lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-800 px-4">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold tracking-tight" onClick={onMobileClose}>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
              B
            </span>
            <span className="text-white">Bhudi</span>
          </Link>
          <button type="button" className="rounded-md p-1 text-slate-400 hover:bg-slate-800 lg:hidden" onClick={onMobileClose}>
            <X size={18} />
          </button>
        </div>

        <div className="border-b border-slate-800 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Workspace</p>
          <button type="button" className="mt-1 flex w-full items-center justify-between rounded-lg py-1 text-left hover:bg-slate-800/60">
            <span className="truncate text-sm font-medium text-slate-200">{user?.email || 'Bhudi Workspace'}</span>
            <ChevronRight size={15} className="shrink-0 text-slate-500" />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3" aria-label="Main navigation">
          {NAV_ITEMS.map((item, index) => {
            const active = isActivePath(pathname, item);
            const Icon = item.icon;
            return (
              <MotionLink
                key={`${item.href}-${item.label}`}
                href={item.href}
                onClick={onMobileClose}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...SPRING, delay: index * 0.012 }}
                aria-current={active ? 'page' : undefined}
                className={`group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  active
                    ? 'bg-indigo-600/20 font-semibold text-indigo-300'
                    : 'font-medium text-slate-400 hover:bg-slate-800/90 hover:text-white'
                }`}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 h-6 w-0.5 -translate-y-1/2 rounded-r-full bg-indigo-400" />
                )}
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${
                    active ? 'bg-indigo-600/30 text-indigo-300' : 'text-slate-500 group-hover:text-indigo-300'
                  }`}
                >
                  <Icon size={17} strokeWidth={active ? 2.25 : 1.75} />
                </span>
                <span className="min-w-0 flex-1 truncate">{item.label}</span>
                {item.badge && (
                  <span className="rounded-full bg-indigo-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-300">
                    {item.badge}
                  </span>
                )}
              </MotionLink>
            );
          })}
        </nav>

        <div className="shrink-0 border-t border-slate-800 p-2">
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-red-400 transition-colors hover:bg-red-950/40 hover:text-red-300"
          >
            <LogOut size={17} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
    </>
  );
}
