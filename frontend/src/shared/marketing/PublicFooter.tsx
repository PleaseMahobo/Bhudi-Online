import Link from 'next/link';
import BhudiLogo from '@/shared/components/BhudiLogo';

const COLUMNS = [
  {
    title: 'Product',
    links: [
      { href: '/features', label: 'Features' },
      { href: '/pricing', label: 'Pricing' },
      { href: '/integrations', label: 'Integrations' },
      { href: '/features#ai', label: 'Bhudi AI' },
    ],
  },
  {
    title: 'Solutions',
    links: [
      { href: '/solutions', label: 'For MSPs' },
      { href: '/solutions', label: 'Enterprise IT' },
      { href: '/documentation', label: 'Documentation' },
    ],
  },
  {
    title: 'Company',
    links: [
      { href: '/about', label: 'About' },
      { href: '/contact', label: 'Contact' },
      { href: '/login', label: 'Sign in' },
      { href: '/signup', label: 'Start free trial' },
    ],
  },
];

export default function PublicFooter() {
  return (
    <footer className="border-t border-slate-800 bg-[#0F172A] text-slate-300">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-4">
        <div>
          <BhudiLogo href="/" size="md" inverted withWordmark />
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            AI-powered IT operations for MSPs and enterprise teams. Monitor, manage, and secure every
            endpoint — with intelligence built in.
          </p>
        </div>

        {COLUMNS.map((col) => (
          <div key={col.title}>
            <h3 className="text-sm font-semibold text-white">{col.title}</h3>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) => (
                <li key={l.href + l.label}>
                  <Link href={l.href} className="text-sm text-slate-400 hover:text-white">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-slate-800">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-6 text-xs text-slate-500 sm:px-6">
          <span>© {new Date().getFullYear()} Bhudi RMM. All rights reserved.</span>
          <span>Big Brother approach to remote monitoring, management and security.</span>
        </div>
      </div>
    </footer>
  );
}
