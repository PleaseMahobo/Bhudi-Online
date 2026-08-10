'use client';

import Link from 'next/link';

type Props = {
  withWordmark?: boolean;
  size?: 'sm' | 'md' | 'lg';
  href?: string | null;
  className?: string;
  inverted?: boolean;
};

const SIZES = {
  sm: 28,
  md: 36,
  lg: 48,
};

/**
 * Official Bhudi RMM brand mark (shield + upward arrows).
 * Uses /brand/bhudi-logo.png when present, else vector mark.
 */
export default function BhudiLogo({
  withWordmark = true,
  size = 'md',
  href = '/',
  className = '',
  inverted = false,
}: Props) {
  const px = SIZES[size];
  const content = (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <span
        className="relative shrink-0 overflow-hidden rounded-lg bg-transparent"
        style={{ width: px, height: px }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/brand/bhudi-logo.png"
          alt="Bhudi RMM"
          width={px}
          height={px}
          className="h-full w-full object-contain"
          onError={(e) => {
            const el = e.currentTarget;
            if (!el.dataset.fallback) {
              el.dataset.fallback = '1';
              el.src = '/brand/bhudi-mark.svg';
            }
          }}
        />
      </span>
      {withWordmark && (
        <span className="flex flex-col leading-none">
          <span
            className={
              'text-sm font-bold tracking-tight ' + (inverted ? 'text-white' : 'text-slate-900')
            }
          >
            Bhudi
            <span className="text-indigo-500"> RMM</span>
          </span>
          {size !== 'sm' && (
            <span
              className={
                'mt-0.5 hidden text-[10px] font-medium sm:block ' +
                (inverted ? 'text-slate-400' : 'text-slate-500')
              }
            >
              Monitor · Manage · Secure
            </span>
          )}
        </span>
      )}
    </span>
  );

  if (href === null) return content;
  return (
    <Link href={href} className="inline-flex shrink-0 items-center" aria-label="Bhudi RMM home">
      {content}
    </Link>
  );
}
