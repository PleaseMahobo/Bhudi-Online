import Link from 'next/link';
import { Sparkles } from 'lucide-react';

const COLUMNS = [
  {
    title: 'Product',
    links: [
      { href: '/features', label: 'Features' },
      { href: '/solutions', label: 'Solutions' },
      { href: '/pricing', label: 'Pricing' },
      { href: '/integrations', label: 'Integrations' },
      { href: '/trial', label: 'Start Free Trial' },
    ],
  },
  {
    title: 'Company',
    links: [
      { href: '/about', label: 'About' },
      { href: '/contact', label: 'Contact' },
      { href: '/documentation', label: 'Documentation' },
      { href: '/login', label: 'Login' },
    ],
  },
  {
    title: 'Platform',
    links: [
      { href: '/features#ai', label: 'Bhudi AI' },
      { href: '/features#rmm', label: 'RMM & Devices' },
      { href: '/features#print', label: 'Print Management' },
      { href: '/features#security', label: 'Endpoint Security' },
    ],
  },
];

export default function PublicFooter() {
  return (
    <footer className="border-t border-slate-800 bg-[#0F172A] text-slate-300">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-4">
        <div>
          <div className="flex items-center gap-2.5 font-semibold text-white">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600">
              <Sparkles size={16} />
            </span>
            Bhudi
          </div>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            AI-powered IT operations for MSPs and enterprise teams. Monitor,
            manage, and secure every endpoint — with intelligence built in.
          </p>
        </div>

        {COLUMNS.map((col) => (
          <div key={col.title}>
            <h3 className="text-sm font-semibold text-white">{col.title}</h3>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-400 transition hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="border-t border-slate-800">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span>© {new Date().getFullYear()} Bhudi. All rights reserved.</span>
          <span>Built for MSPs &amp; Enterprise IT</span>
        </div>
      </div>
    </footer>
  );
}
