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
import BhudiLogo from '@/shared/components/BhudiLogo';

type NavItem = { label: string; href: string; icon: LucideIcon; exact?: boolean; badge?: string };

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, exact: true },
  { label: 'Devices', href: '/devices', icon: Monitor },
  { label: 'Download Agent', href: '/agents', icon: Download },
  { label: 'Customers', href: '/msp', icon: Users },
  { label: 'Tickets', href: '/itsm', icon: Ticket, badge: '3' },
  { label: 'Alerts', href: '/alert-engine', icon: Activity },
  { label: 'Automation', href: '/commands', icon: Zap },
  { label: 'Remote Access', href: '/remote', icon: ScreenShare },
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
        <div className="fixed inset-0 z-40 bg-slate-900/40 md:hidden" onClick={onMobileClose} aria-hidden />
      )}
      {/*
        Desktop (md+): in-flow flex child (shrink-0 w-64) — no fixed, no content margin.
        Mobile: fixed overlay drawer.
      */}
      <aside
        className={
          'z-50 flex w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-950 text-slate-100 ' +
          'fixed inset-y-0 left-0 transition-transform duration-200 ease-out ' +
          (mobileOpen ? 'translate-x-0' : '-translate-x-full') +
          ' md:static md:translate-x-0'
        }
      >
        <div className="flex h-14 items-center justify-between border-b border-white/10 px-4">
          <BhudiLogo href="/dashboard" size="sm" inverted withWordmark variant="mark" />
          <button type="button" className="md:hidden text-slate-400" onClick={onMobileClose}>
            <X size={18} />
          </button>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const active = isActivePath(pathname, item);
            const Icon = item.icon;
            return (
              <MotionLink
                key={item.href + item.label}
                href={item.href}
                onClick={onMobileClose}
                className={
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ' +
                  (active
                    ? 'bg-indigo-600/90 text-white'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white')
                }
                whileTap={{ scale: 0.98 }}
                transition={SPRING}
              >
                <Icon size={16} className="shrink-0 opacity-90" />
                <span className="flex-1 truncate">{item.label}</span>
                {item.badge && (
                  <span className="rounded-full bg-white/15 px-1.5 text-[10px] font-semibold">
                    {item.badge}
                  </span>
                )}
                {active && <ChevronRight size={14} className="opacity-70" />}
              </MotionLink>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-3">
          <div className="mb-2 truncate px-2 text-xs text-slate-400">{user?.email || 'Signed in'}</div>
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
