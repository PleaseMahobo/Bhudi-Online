'use client';

import Link from 'next/link';
import { BHUDI_LOGO_DATA_URL } from '@/shared/brand/logoData';

type Props = {
  withWordmark?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  href?: string | null;
  className?: string;
  inverted?: boolean;
  variant?: 'full' | 'mark';
};

const BOX = {
  sm: 36,
  md: 40,
  lg: 120,
  xl: 160,
} as const;

/**
 * Official Cyber Bastion / Bhudi RMM logo (metallic chrome mark).
 * Prefers /brand/bhudi-logo.png, falls back to embedded asset.
 */
export default function BhudiLogo({
  withWordmark = false,
  size = 'md',
  href = '/',
  className = '',
  inverted = false,
  variant = 'mark',
}: Props) {
  const px = BOX[size];
  const isFull = variant === 'full' || size === 'lg' || size === 'xl';

  const img = (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/brand/bhudi-logo.png"
      alt="Bhudi RMM — Cyber Bastion"
      width={isFull ? px * 1.15 : px}
      height={px}
      className={
        isFull
          ? 'mx-auto h-auto w-full max-w-[220px] object-contain drop-shadow-lg'
          : 'h-full w-full object-contain'
      }
      onError={(e) => {
        const el = e.currentTarget;
        if (el.dataset.fallback === 'data') return;
        if (!el.dataset.fallback) {
          el.dataset.fallback = 'data';
          el.src = BHUDI_LOGO_DATA_URL;
        }
      }}
    />
  );

  const content = (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <span
        className={
          isFull
            ? 'relative block w-full max-w-[220px]'
            : 'relative shrink-0 overflow-hidden rounded-lg bg-transparent'
        }
        style={isFull ? undefined : { width: px, height: px }}
      >
        {img}
      </span>
      {withWordmark && !isFull && (
        <span className="flex flex-col leading-none">
          <span
            className={
              'text-sm font-bold tracking-tight ' + (inverted ? 'text-white' : 'text-slate-900')
            }
          >
            Bhudi
            <span className="text-indigo-400"> RMM</span>
          </span>
          <span
            className={
              'mt-0.5 hidden text-[10px] font-medium sm:block ' +
              (inverted ? 'text-slate-400' : 'text-slate-500')
            }
          >
            Cyber Bastion
          </span>
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
