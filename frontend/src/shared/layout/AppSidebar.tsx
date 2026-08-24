'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { motion, type Transition } from 'framer-motion';
import {
  Activity,
  BarChart3,
  ChevronRight,
  Download,
  LayoutDashboard,
  LogOut,
  Monitor,
  Settings,
  Ticket,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/shared/auth/AuthContext';
import BhudiLogo from '@/shared/components/BhudiLogo';

type NavItem = { label: string; href: string; icon: LucideIcon; exact?: boolean; badge?: string };

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, exact: true },
  { label: 'Sites', href: '/msp', icon: Users },
  { label: 'Devices', href: '/devices', icon: Monitor },
  { label: 'Alerts', href: '/alert-engine', icon: Activity },
  { label: 'Tickets', href: '/itsm', icon: Ticket },
  { label: 'Agents', href: '/agents', icon: Download },
  { label: 'Reports', href: '/reporting', icon: BarChart3 },
  { label: 'Administration', href: '/compliance', icon: Settings },
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
        <div className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden" onClick={onMobileClose} />
      )}
      <aside
        className={
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-slate-950 text-slate-100 transition-transform lg:static lg:translate-x-0 ' +
          (mobileOpen ? 'translate-x-0' : '-translate-x-full')
        }
      >
        <div className="flex h-14 items-center justify-between border-b border-white/10 px-4">
          <BhudiLogo href="/dashboard" size="sm" inverted withWordmark variant="mark" />
          <button type="button" className="lg:hidden text-slate-400" onClick={onMobileClose} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>

        <div className="border-b border-white/10 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">RMM Console</p>
          <p className="mt-1 text-xs text-slate-300">IT operations & endpoint management</p>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => {
            const active = isActivePath(pathname, item);
            const Icon = item.icon;
            return (
              <MotionLink
                key={item.href + item.label}
                href={item.href}
                onClick={onMobileClose}
                className={
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ' +
                  (active
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white')
                }
                whileTap={{ scale: 0.98 }}
                transition={SPRING}
              >
                <Icon size={17} className="shrink-0 opacity-90" />
                <span className="flex-1 truncate">{item.label}</span>
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
