'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  Building2,
  LayoutDashboard,
  Monitor,
  ScreenShare,
  Settings,
  Terminal,
} from 'lucide-react';
import DeepBuddyLogo from './DeepBuddyLogo';

const NAV = [
  { href: '/deep-buddy/console', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { href: '/deep-buddy/console/clients', label: 'Clients & Sites', icon: Building2 },
  { href: '/deep-buddy/console/agents', label: 'Agents', icon: Monitor },
  { href: '/deep-buddy/console/remote', label: 'Remote', icon: ScreenShare },
  { href: '/deep-buddy/console/scripts', label: 'Scripts', icon: Terminal },
  { href: '/deep-buddy/console/alerts', label: 'Alerts', icon: Activity },
  { href: '/deep-buddy/console/settings', label: 'Settings', icon: Settings },
];

export default function ConsoleShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-slate-100 text-slate-900">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-950 text-slate-100">
        <div className="border-b border-white/10 px-4 py-3">
          <DeepBuddyLogo href="/deep-buddy/console" inverted size="sm" />
        </div>
        <nav className="flex-1 space-y-0.5 p-3">
          {NAV.map((item) => {
            const active = item.exact
              ? pathname === item.href
              : pathname === item.href || pathname.startsWith(item.href + '/');
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ' +
                  (active
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white')
                }
              >
                <Icon size={16} className="opacity-90" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-3 text-[11px] text-slate-500">
          Inspired by Tactical RMM patterns · Powered by Bhudi agent runtime
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center justify-between border-b border-slate-200 bg-white px-5">
          <span className="text-sm font-medium text-slate-600">Deep Buddy Console</span>
          <Link href="/deep-buddy" className="text-xs text-cyan-700 hover:underline">
            Marketing site
          </Link>
        </header>
        <main className="flex-1 overflow-auto p-5">{children}</main>
      </div>
    </div>
  );
}
