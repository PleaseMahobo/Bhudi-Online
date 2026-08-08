'use client';

import { useEffect } from 'react';
import { useRetryReset } from '@/shared/lib/useRetryReset';

/**
 * Root-level error boundary for the App Router.
 * Must render its own <html> and <body> because it replaces the root layout
 * when an error occurs there.
 */
export default function GlobalError({
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
    console.error('[Bhudi] Global application error:', error);
  }, [error]);

  const statusText = isRetrying
    ? `Retrying… (attempt ${attempts} of ${maxAttempts})`
    : exhausted
      ? 'Automatic recovery failed. Go home or try again later.'
      : 'A critical error stopped the application from loading. Retry the page or return home.';

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f8fafc',
          fontFamily:
            'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
          color: '#0f172a',
          padding: 24,
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 480,
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: 16,
            boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
            padding: 32,
            textAlign: 'center',
          }}
        >
          <div
            style={{
              margin: '0 auto 20px',
              width: 56,
              height: 56,
              borderRadius: 16,
              background: '#fef2f2',
              color: '#ef4444',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 28,
              fontWeight: 700,
            }}
            aria-hidden
          >
            !
          </div>

          <h1
            style={{
              margin: 0,
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: '-0.02em',
            }}
          >
            Bhudi encountered a problem
          </h1>
          <p
            style={{
              margin: '12px 0 0',
              fontSize: 14,
              lineHeight: 1.55,
              color: '#64748b',
            }}
          >
            {statusText}
          </p>

          {attempts > 0 && !exhausted && !isRetrying && (
            <p style={{ margin: '8px 0 0', fontSize: 12, color: '#94a3b8' }}>
              Attempts used: {attempts}/{maxAttempts}
            </p>
          )}

          {error?.digest && (
            <p
              style={{
                margin: '16px 0 0',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                fontSize: 12,
                color: '#94a3b8',
                wordBreak: 'break-all',
              }}
            >
              Error ID: {error.digest}
            </p>
          )}

          <div
            style={{
              marginTop: 28,
              display: 'flex',
              flexWrap: 'wrap',
              gap: 12,
              justifyContent: 'center',
            }}
          >
            <button
              type="button"
              onClick={retry}
              disabled={isRetrying || exhausted}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                border: 'none',
                borderRadius: 12,
                background: isRetrying || exhausted ? '#93c5fd' : '#2563eb',
                color: '#ffffff',
                fontSize: 14,
                fontWeight: 500,
                padding: '10px 20px',
                cursor: isRetrying || exhausted ? 'not-allowed' : 'pointer',
                opacity: isRetrying || exhausted ? 0.7 : 1,
              }}
            >
              {isRetrying ? 'Retrying…' : exhausted ? 'Retries exhausted' : 'Try again'}
            </button>
            <a
              href="/"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                border: '1px solid #e2e8f0',
                borderRadius: 12,
                background: '#ffffff',
                color: '#334155',
                fontSize: 14,
                fontWeight: 500,
                padding: '10px 20px',
                textDecoration: 'none',
              }}
            >
              Go home
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
