import Link from 'next/link';
import { PageHero, SectionLabel } from '@/shared/marketing/MarketingUI';
import { BLOG_POSTS } from '@/shared/marketing/blog';

export const metadata = {
  title: 'Blog — Bhudi',
  description: 'Product thinking on RMM, remote access, agents, and MSP operations.',
};

export default function BlogIndexPage() {
  return (
    <>
      <PageHero
        label="Blog"
        title="Notes from the operations floor"
        subtitle="Practical writing on agents, remote control, print, and how MSPs actually work."
        primaryHref="/changelog"
        primaryLabel="Changelog"
      />

      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <SectionLabel>Latest</SectionLabel>
        <ul className="mt-8 space-y-6">
          {BLOG_POSTS.map((post) => (
            <li key={post.slug}>
              <Link
                href={`/blog/${post.slug}`}
                className="block rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <time>{post.date}</time>
                  {post.tags.map((t) => (
                    <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                      {t}
                    </span>
                  ))}
                </div>
                <h2 className="mt-3 text-xl font-semibold text-[#0F172A]">{post.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{post.excerpt}</p>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
