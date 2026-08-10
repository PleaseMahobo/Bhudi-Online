import Link from 'next/link';
import BhudiLogo from '@/shared/components/BhudiLogo';

const COLS = [
  {
    title: 'Product',
    links: [
      { href: '/features', label: 'Features' },
      { href: '/solutions', label: 'Solutions' },
      { href: '/pricing', label: 'Pricing' },
      { href: '/integrations', label: 'Integrations' },
      { href: '/agents', label: 'Download agent' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { href: '/documentation', label: 'Documentation' },
      { href: '/trial', label: 'Free trial' },
      { href: '/remote', label: 'Remote access' },
      { href: '/login', label: 'Log in' },
    ],
  },
  {
    title: 'Company',
    links: [
      { href: '/about', label: 'About' },
      { href: '/contact', label: 'Contact' },
      { href: '/signup', label: 'Sign up' },
    ],
  },
];

export default function PublicFooter() {
  return (
    <footer className="border-t border-slate-200 bg-[#0F172A] text-slate-300">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="grid gap-10 md:grid-cols-4">
          <div>
            <BhudiLogo href="/" size="md" withWordmark inverted />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-slate-400">
              AI-powered IT operations for MSPs and enterprise teams — monitor, manage, and
              secure from one modern workspace.
            </p>
          </div>
          {COLS.map((col) => (
            <div key={col.title}>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {col.title}
              </p>
              <ul className="mt-4 space-y-2">
                {col.links.map((l) => (
                  <li key={l.href}>
                    <Link href={l.href} className="text-sm text-slate-300 hover:text-white">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col gap-2 border-t border-white/10 pt-8 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Bhudi. All rights reserved.</p>
          <p>Monitor · Manage · Secure</p>
        </div>
      </div>
    </footer>
  );
}
