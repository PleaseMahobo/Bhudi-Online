'use client';

import React, { useState } from 'react';
import { seedAlertDefaults } from '@/lib/alert-seed';
import type { AlertRule, EscalationPolicy } from '@/lib/api';

export default function SeedDefaultsButton({
  onSeeded,
  className = '',
  label = 'Seed defaults',
}: {
  onSeeded?: (rules: AlertRule[], policies: EscalationPolicy[], message: string) => void;
  className?: string;
  label?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    try {
      setBusy(true);
      setError(null);
      const result = await seedAlertDefaults(false);
      onSeeded?.(
        Array.isArray(result.rules) ? result.rules : [],
        Array.isArray(result.policies) ? result.policies : [],
        result.message || `Seeded ${result.created} rules`
      );
    } catch (e: any) {
      setError(e?.message || 'Seed failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={run}
        disabled={busy}
        className={
          className ||
          'flex items-center gap-2 rounded-xl bg-zinc-800 px-4 py-2.5 text-sm font-medium transition hover:bg-zinc-700 disabled:opacity-50'
        }
      >
        {busy ? 'Seeding…' : label}
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}
