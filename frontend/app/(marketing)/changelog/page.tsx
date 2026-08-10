import Link from 'next/link';
import { PageHero, SectionLabel } from '@/shared/marketing/MarketingUI';
import { CHANGELOG } from '@/shared/marketing/changelog';

export const metadata = {
  title: 'Changelog — Bhudi',
  description: 'Product updates for the Bhudi agent, remote access, and operations platform.',
};

export default function ChangelogPage() {
  return (
    <>
      <PageHero
        label="Changelog"
        title="What shipped recently"
        subtitle="Agent, remote access, and platform updates — written for operators, not only engineers."
        primaryHref="/agents"
        primaryLabel="Download agent"
        secondaryHref="/documentation"
        secondaryLabel="Docs"
      />

      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <SectionLabel>Releases</SectionLabel>
        <ol className="mt-8 space-y-10">
          {CHANGELOG.map((entry) => (
            <li key={entry.version} className="relative border-l-2 border-indigo-100 pl-6">
              <span className="absolute -left-[7px] top-1.5 h-3 w-3 rounded-full bg-indigo-500" />
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-slate-900 px-2.5 py-0.5 text-xs font-semibold text-white">
                  v{entry.version}
                </span>
                <time className="text-xs text-slate-500">{entry.date}</time>
                {entry.tags.map((t) => (
                  <span
                    key={t}
                    className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700"
                  >
                    {t}
                  </span>
                ))}
              </div>
              <h2 className="mt-3 text-lg font-semibold text-[#0F172A]">{entry.title}</h2>
              <ul className="mt-3 space-y-2">
                {entry.body.map((line) => (
                  <li key={line} className="text-sm leading-relaxed text-slate-600">
                    • {line}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
        <p className="mt-12 text-sm text-slate-500">
          Looking for how-to guides? See{' '}
          <Link href="/documentation" className="font-semibold text-indigo-600">
            documentation
          </Link>
          .
        </p>
      </section>
    </>
  );
}
