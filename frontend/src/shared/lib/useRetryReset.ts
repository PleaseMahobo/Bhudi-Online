'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type RetryResetOptions = {
  /** Next.js / React reset callback */
  reset: () => void;
  /** Maximum number of reset attempts (manual + auto). Default 3 */
  maxAttempts?: number;
  /** Base delay in ms for exponential backoff. Default 800 */
  baseDelayMs?: number;
  /** Cap delay in ms. Default 5000 */
  maxDelayMs?: number;
  /** Automatically retry once after the first error. Default true */
  autoRetry?: boolean;
  /** Delay before the automatic first retry. Default 1200 */
  autoRetryDelayMs?: number;
};

export type RetryResetState = {
  attempts: number;
  maxAttempts: number;
  isRetrying: boolean;
  exhausted: boolean;
  nextDelayMs: number;
  retry: () => void;
};

function clampDelay(base: number, attempt: number, max: number) {
  // attempt is 0-based for delay calculation after the first failure
  const ms = Math.min(max, base * 2 ** Math.max(0, attempt - 1));
  // small jitter so concurrent clients don't stampede
  const jitter = Math.floor(Math.random() * Math.min(200, ms * 0.15));
  return ms + jitter;
}

/**
 * Adds limited retries + exponential backoff around Next.js `reset()`
 * (or any recovery callback).
 */
export function useRetryReset({
  reset,
  maxAttempts = 3,
  baseDelayMs = 800,
  maxDelayMs = 5000,
  autoRetry = true,
  autoRetryDelayMs = 1200,
}: RetryResetOptions): RetryResetState {
  const [attempts, setAttempts] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const attemptsRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoDoneRef = useRef(false);
  const resetRef = useRef(reset);
  resetRef.current = reset;

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => () => clearTimer(), []);

  const runReset = useCallback((nextAttempt: number) => {
    clearTimer();
    setIsRetrying(true);
    const delay = nextAttempt <= 1 ? 0 : clampDelay(baseDelayMs, nextAttempt, maxDelayMs);

    timerRef.current = setTimeout(() => {
      try {
        resetRef.current();
      } finally {
        // Keep "retrying" briefly so the button does not flash if reset is sync
        timerRef.current = setTimeout(() => setIsRetrying(false), 400);
      }
    }, delay);
  }, [baseDelayMs, maxDelayMs]);

  const retry = useCallback(() => {
    if (isRetrying) return;
    if (attemptsRef.current >= maxAttempts) return;

    const next = attemptsRef.current + 1;
    attemptsRef.current = next;
    setAttempts(next);
    console.info(`[Bhudi] Error boundary retry ${next}/${maxAttempts}`);
    runReset(next);
  }, [isRetrying, maxAttempts, runReset]);

  // One automatic retry shortly after the error UI mounts
  useEffect(() => {
    if (!autoRetry || autoDoneRef.current) return;
    autoDoneRef.current = true;

    timerRef.current = setTimeout(() => {
      if (attemptsRef.current >= maxAttempts) return;
      const next = attemptsRef.current + 1;
      attemptsRef.current = next;
      setAttempts(next);
      console.info(`[Bhudi] Error boundary auto-retry ${next}/${maxAttempts}`);
      runReset(next);
    }, autoRetryDelayMs);

    return clearTimer;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const exhausted = attempts >= maxAttempts && !isRetrying;
  const nextDelayMs =
    attempts === 0 ? 0 : clampDelay(baseDelayMs, attempts + 1, maxDelayMs);

  return {
    attempts,
    maxAttempts,
    isRetrying,
    exhausted,
    nextDelayMs,
    retry,
  };
}
