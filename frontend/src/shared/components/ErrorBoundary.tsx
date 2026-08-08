'use client';

import React, { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

type Props = {
  children: ReactNode;
  /** Optional compact fallback for nested panels */
  fallback?: ReactNode;
  /** Called when an error is caught (e.g. telemetry) */
  onError?: (error: Error, info: React.ErrorInfo) => void;
  /** Max reset attempts before the button is disabled. Default 3 */
  maxAttempts?: number;
  /** Auto-retry once after mount when an error is shown. Default true */
  autoRetry?: boolean;
  /** Delay before auto-retry in ms. Default 1200 */
  autoRetryDelayMs?: number;
  /** Base backoff delay for manual retries after the first. Default 800 */
  baseDelayMs?: number;
};

type State = {
  hasError: boolean;
  error: Error | null;
  attempts: number;
  isRetrying: boolean;
};

/**
 * Client-side React error boundary for wrapping interactive subtrees
 * (dashboards, tables, AI panels) without taking down the whole route.
 *
 * Prefer app/error.tsx and app/global-error.tsx for route-level failures.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false,
    error: null,
    attempts: 0,
    isRetrying: false,
  };

  private autoTimer: ReturnType<typeof setTimeout> | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private autoScheduled = false;

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[Bhudi] Component error boundary:', error, info);
    this.props.onError?.(error, info);
    this.scheduleAutoRetry();
  }

  componentWillUnmount() {
    this.clearTimers();
  }

  private clearTimers() {
    if (this.autoTimer) {
      clearTimeout(this.autoTimer);
      this.autoTimer = null;
    }
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }

  private maxAttempts() {
    return this.props.maxAttempts ?? 3;
  }

  private scheduleAutoRetry() {
    if (this.props.autoRetry === false) return;
    if (this.autoScheduled) return;
    this.autoScheduled = true;

    const delay = this.props.autoRetryDelayMs ?? 1200;
    this.autoTimer = setTimeout(() => {
      this.performRetry();
    }, delay);
  }

  private performRetry = () => {
    const max = this.maxAttempts();
    if (this.state.isRetrying || this.state.attempts >= max) return;

    const nextAttempt = this.state.attempts + 1;
    const base = this.props.baseDelayMs ?? 800;
    // First attempt is immediate; later attempts back off
    const delay =
      nextAttempt <= 1 ? 0 : Math.min(5000, base * 2 ** (nextAttempt - 2));

    console.info(`[Bhudi] Component boundary retry ${nextAttempt}/${max}`);
    this.setState({ isRetrying: true, attempts: nextAttempt });

    this.retryTimer = setTimeout(() => {
      this.setState({ hasError: false, error: null, isRetrying: false });
      // Allow a future auto-retry if the same subtree errors again after success
      this.autoScheduled = false;
    }, delay);
  };

  private handleReset = () => {
    this.performRetry();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    const max = this.maxAttempts();
    const { attempts, isRetrying } = this.state;
    const exhausted = attempts >= max && !isRetrying;

    return (
      <div className="rounded-xl border border-red-200 bg-red-50/60 p-6 text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-red-100 text-red-500">
          <AlertTriangle size={20} />
        </div>
        <h3 className="text-sm font-semibold text-slate-900">This section failed to load</h3>
        <p className="mt-1 text-xs text-slate-500">
          {isRetrying
            ? `Retrying… (${attempts}/${max})`
            : exhausted
              ? 'Retries exhausted for this section.'
              : this.state.error?.message ||
                'An unexpected error occurred in this component.'}
        </p>
        {attempts > 0 && !exhausted && !isRetrying && (
          <p className="mt-1 text-[11px] text-slate-400">
            Attempts used: {attempts}/{max}
          </p>
        )}
        <button
          type="button"
          onClick={this.handleReset}
          disabled={isRetrying || exhausted}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed px-3.5 py-2 text-xs font-medium text-white transition"
        >
          <RefreshCw size={14} className={isRetrying ? 'animate-spin' : undefined} />
          {isRetrying ? 'Retrying…' : exhausted ? 'Retries exhausted' : 'Retry'}
        </button>
      </div>
    );
  }
}
