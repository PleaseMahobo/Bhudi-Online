'use client';

import { useEffect } from 'react';
import { AlertTriangle, Home, RefreshCw } from 'lucide-react';
import { useRetryReset } from '@/shared/lib/useRetryReset';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { attempts, maxAttempts, isRetrying, exhausted, retry } = useRetryReset({
    reset,
    maxAttempts: 3,
    autoRetry: true,
  });

  useEffect(() => {
    console.error('[Bhudi] Unhandled route error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-sm p-8 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50 text-red-500">
          <AlertTriangle size={28} strokeWidth={2} />
        </div>

        <h1 className="text-xl font-bold tracking-tight text-slate-900">
          Something went wrong
        </h1>
        <p className="mt-2 text-sm text-slate-500 leading-relaxed">
          {isRetrying
            ? `Retrying… (attempt ${attempts} of ${maxAttempts})`
            : exhausted
              ? 'Automatic recovery failed. Return to the dashboard or try again later.'
              : 'An unexpected error occurred while loading this page. You can try again or return to the dashboard.'}
        </p>

        {attempts > 0 && !exhausted && !isRetrying && (
          <p className="mt-2 text-xs text-slate-400">
            Attempts used: {attempts}/{maxAttempts}
          </p>
        )}

        {error?.digest && (
          <p className="mt-4 font-mono text-xs text-slate-400 break-all">
            Error ID: {error.digest}
          </p>
        )}

        {process.env.NODE_ENV === 'development' && error?.message && (
          <pre className="mt-4 max-h-40 overflow-auto rounded-xl bg-slate-900 text-left text-xs text-red-200 p-4 whitespace-pre-wrap">
            {error.message}
          </pre>
        )}

        <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
          <button
            type="button"
            onClick={retry}
            disabled={isRetrying || exhausted}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed px-5 py-2.5 text-sm font-medium text-white transition"
          >
            <RefreshCw size={16} className={isRetrying ? 'animate-spin' : undefined} />
            {isRetrying ? 'Retrying…' : exhausted ? 'Retries exhausted' : 'Try again'}
          </button>
          <a
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 px-5 py-2.5 text-sm font-medium text-slate-700 transition"
          >
            <Home size={16} />
            Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
