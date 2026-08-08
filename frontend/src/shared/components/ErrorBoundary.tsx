'use client';

import React, { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

type Props = {
  children: ReactNode;
  /** Optional compact fallback for nested panels */
  fallback?: ReactNode;
  /** Called when an error is caught (e.g. telemetry) */
  onError?: (error: Error, info: React.ErrorInfo) => void;
};

type State = {
  hasError: boolean;
  error: Error | null;
};

/**
 * Client-side React error boundary for wrapping interactive subtrees
 * (dashboards, tables, AI panels) without taking down the whole route.
 *
 * Prefer app/error.tsx and app/global-error.tsx for route-level failures.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[Bhudi] Component error boundary:', error, info);
    this.props.onError?.(error, info);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <div className="rounded-xl border border-red-200 bg-red-50/60 p-6 text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-red-100 text-red-500">
          <AlertTriangle size={20} />
        </div>
        <h3 className="text-sm font-semibold text-slate-900">This section failed to load</h3>
        <p className="mt-1 text-xs text-slate-500">
          {this.state.error?.message || 'An unexpected error occurred in this component.'}
        </p>
        <button
          type="button"
          onClick={this.handleReset}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3.5 py-2 text-xs font-medium text-white transition"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      </div>
    );
  }
}
