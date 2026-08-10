import Link from 'next/link';
import { notFound } from 'next/navigation';
import { BLOG_POSTS, getPost } from '@/shared/marketing/blog';

export function generateStaticParams() {
  return BLOG_POSTS.map((p) => ({ slug: p.slug }));
}

export function generateMetadata({ params }: { params: { slug: string } }) {
  const post = getPost(params.slug);
  if (!post) return { title: 'Post — Bhudi' };
  return { title: `${post.title} — Bhudi`, description: post.excerpt };
}

export default function BlogPostPage({ params }: { params: { slug: string } }) {
  const post = getPost(params.slug);
  if (!post) notFound();

  return (
    <article className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <Link href="/blog" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
        ← Blog
      </Link>
      <div className="mt-6 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <time>{post.date}</time>
        {post.tags.map((t) => (
          <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5">
            {t}
          </span>
        ))}
      </div>
      <h1 className="mt-4 text-3xl font-bold tracking-tight text-[#0F172A] sm:text-4xl">
        {post.title}
      </h1>
      <div className="mt-8 space-y-4 text-base leading-relaxed text-slate-700">
        {post.body.map((p) => (
          <p key={p.slice(0, 40)}>{p}</p>
        ))}
      </div>
    </article>
  );
}
