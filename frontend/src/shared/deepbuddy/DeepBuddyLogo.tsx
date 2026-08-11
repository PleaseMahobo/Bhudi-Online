'use client';

import Link from 'next/link';

type Props = {
  href?: string | null;
  size?: 'sm' | 'md' | 'lg';
  inverted?: boolean;
  className?: string;
};

export default function DeepBuddyLogo({
  href = '/deep-buddy',
  size = 'md',
  inverted = false,
  className = '',
}: Props) {
  const text = inverted ? 'text-white' : 'text-slate-900';
  const sub = inverted ? 'text-cyan-300' : 'text-cyan-700';
  const mark =
    size === 'sm' ? 'h-8 w-8 text-xs' : size === 'lg' ? 'h-12 w-12 text-base' : 'h-9 w-9 text-sm';

  const body = (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <span
        className={`flex ${mark} items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-700 font-black text-white shadow-lg shadow-cyan-500/20`}
      >
        DB
      </span>
      <span className="flex flex-col leading-none">
        <span className={`text-sm font-bold tracking-tight ${text}`}>
          Deep<span className={sub}>Buddy</span>
        </span>
        <span
          className={`mt-0.5 text-[10px] font-medium ${
            inverted ? 'text-slate-400' : 'text-slate-500'
          }`}
        >
          Tactical-class RMM
        </span>
      </span>
    </span>
  );

  if (href === null) return body;
  return (
    <Link href={href} className="inline-flex shrink-0" aria-label="Deep Buddy home">
      {body}
    </Link>
  );
}
